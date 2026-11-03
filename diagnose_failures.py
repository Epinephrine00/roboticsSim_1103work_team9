"""Classify the failed rollouts of eval_multienv.py into approach / grasp / carry / place failures.

    python diagnose_failures.py logs/.../model_epoch_2000_rollouts.npz [--csv out.csv]

Rules (all positions are in the robot base frame, as in the policy observations):
  approach : the hand never came within --reach of the toy
  grasp    : the hand reached the toy but the toy was never lifted by --lift above its start height
  carry    : the toy was lifted but never came within --near (xy) of the box centre
  place    : the toy came near the box but the episode still did not succeed (left on the rim, dropped outside,
             gripper not opened in time, ...)
The thresholds are heuristics; check a few rollouts by eye before quoting the numbers.
"""

import argparse
import csv

import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("npz")
parser.add_argument("--reach", type=float, default=0.08, help="hand-to-toy distance [m] that counts as reaching it (successful human demos: 0.01-0.05)")
parser.add_argument("--lift", type=float, default=0.05, help="toy height gain [m] that counts as lifted (successful human demos: 0.33-0.63)")
parser.add_argument("--near", type=float, default=0.15, help="toy-to-box xy distance [m] that counts as near the box")
parser.add_argument("--csv", type=str, default=None, help="write the per-rollout table here")
args = parser.parse_args()

rollouts = np.load(args.npz, allow_pickle=True)["rollouts"]
rows = []
for i, r in enumerate(rollouts):
    eef, toy, box, grip = r["eef_pos"], r["toy_truck_positions"], r["box_positions"], r["gripper_pos"]
    d_hand_toy = np.linalg.norm(eef - toy, axis=1)
    lift = toy[:, 2] - toy[0, 2]
    d_toy_box = np.linalg.norm(toy[:, :2] - box[:, :2], axis=1)
    closed = grip[:, 0] > -0.6  # gripper_pos observation: -0.99 when open, -0.2 .. -0.4 when closed on the toy (measured on the human demos)
    closed[:3] = False  # the first steps after a reset read 0 before the fingers settle
    reached = bool(d_hand_toy.min() < args.reach)
    lifted = bool(lift.max() > args.lift)
    near_box = bool(d_toy_box.min() < args.near)
    if r["success"]:
        stage = "success"
    elif not reached:
        stage = "approach"
    elif not lifted:
        stage = "grasp"
    elif not near_box:
        stage = "carry"
    else:
        stage = "place"
    rows.append({
        "rollout": i, "result": stage, "steps": int(r["end_step"]), "dropped": bool(r["dropped"]),
        "min_hand_toy_m": round(float(d_hand_toy.min()), 3), "max_lift_m": round(float(lift.max()), 3),
        "min_toy_box_xy_m": round(float(d_toy_box.min()), 3),
        "grip_switches": int((np.diff(closed.astype(int)) != 0).sum()),
        "idle_frac": round(float((np.abs(r["actions"][:, :6]) < 1e-6).all(axis=1).mean()), 2),
    })

n = len(rows)
n_ok = sum(r["result"] == "success" for r in rows)
print(f"rollouts: {n}  success: {n_ok} ({n_ok / n:.0%})")
fails = [r for r in rows if r["result"] != "success"]
for stage in ("approach", "grasp", "carry", "place"):
    k = sum(r["result"] == stage for r in fails)
    print(f"  {stage:<9s} {k:3d}  ({k / max(len(fails), 1):.0%} of failures)")
ok_steps = [r["steps"] for r in rows if r["result"] == "success"]
if ok_steps:
    print(f"success length: mean {np.mean(ok_steps):.0f} steps, min {min(ok_steps)}, max {max(ok_steps)}")
print()
hdr = ("rollout", "result", "steps", "dropped", "min_hand_toy_m", "max_lift_m", "min_toy_box_xy_m", "grip_switches", "idle_frac")
print("  ".join(f"{h:>16s}" if h != "rollout" else f"{h:>7s}" for h in hdr))
for r in rows:
    print("  ".join(f"{str(r[h]):>16s}" if h != "rollout" else f"{r[h]:>7d}" for h in hdr))
if args.csv:
    with open(args.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(hdr))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {args.csv}")
