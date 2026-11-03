"""Example rollouts after a failed first grasp: clean162-trained policy (no recovery) vs dirty162-trained policy
(re-closes and lifts).  Writes analysis/fig_recovery_examples.png.  Usage: python analysis/plot_recovery_examples.py"""
import glob, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regrasp_analysis import analyse

BLUE, ORANGE, AQUA, INK, INK2, GRID, AXIS = "#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.titlecolor": INK, "savefig.dpi": 160})
T = "logs/robomimic/Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0"

def load(name):
    npz = sorted(glob.glob(f"{T}/{name}/*/models/model_epoch_2000_rollouts.npz"))[-1]
    return np.load(npz, allow_pickle=True)["rollouts"], analyse(npz)

def pick(name, want_recovery):
    roll, rows = load(name)
    cands = []
    for i, (r, m) in enumerate(zip(roll, rows)):
        if not (m["reached"] and m["n_close"] > 0 and m["first_ok"] is False): continue
        t0 = int(np.argmax(r["actions"][:, 6] < 0))  # first close must happen at the toy (hand within 8 cm), not at the start
        if np.linalg.norm(r["eef_pos"][t0] - r["toy_truck_positions"][t0]) > 0.08 or t0 < 20: continue
        if want_recovery and m["later_ok"] and m["success"]: cands.append((m["steps"], i))
        if not want_recovery and not m["later_ok"] and not m["success"] and m["n_close"] >= 3: cands.append((-m["n_close"], i))
    cands.sort()
    i = cands[len(cands) // 2][1] if want_recovery else cands[0][1]
    return roll[i], rows[i], i

ex = [("clean162 policy: first grasp fails, no recovery", pick("bc_rnn_clean162_seed101", False), BLUE),
      ("dirty162 policy: first grasp fails, re-grasp succeeds", pick("bc_rnn_dirty162_seed101", True), ORANGE)]
fig, axes = plt.subplots(3, 2, figsize=(8.0, 4.8), sharex="col")
for c, (title, (r, m, idx), col) in enumerate(ex):
    Tt = np.arange(len(r["actions"])) / 20.0
    a = r["actions"][:, 6]; grip = r["gripper_pos"][:, 0]; lift = r["toy_truck_positions"][:, 2] - r["toy_truck_positions"][0, 2]
    axes[0, c].step(Tt, a, where="post", color=col, lw=1.2); axes[0, c].set_ylim(-1.3, 1.3); axes[0, c].set_yticks([-1, 1]); axes[0, c].set_yticklabels(["close", "open"])
    axes[0, c].set_title(f"{title}\n(rollout {idx}: {m['n_close']} close segments, {'success' if m['success'] else 'failure'})", fontsize=9)
    axes[1, c].plot(Tt, grip, color=col, lw=1.2); axes[1, c].set_ylim(-1.05, 0.05)
    axes[2, c].plot(Tt, lift, color=AQUA, lw=1.2); axes[2, c].set_ylim(-0.05, 0.7); axes[2, c].set_xlabel("time [s]")
    for ax in axes[:, c]: ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
axes[0, 0].set_ylabel("gripper\ncommand"); axes[1, 0].set_ylabel("gripper_pos\nobservation"); axes[2, 0].set_ylabel("toy height\ngain [m]")
fig.tight_layout(); fig.savefig("analysis/fig_recovery_examples.png"); print("wrote analysis/fig_recovery_examples.png")
