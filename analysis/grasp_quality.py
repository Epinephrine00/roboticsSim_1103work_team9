"""Per-demo grasp quality of a dataset: offset/speed at the first close command, lift after it, slips, obs toggles.
Usage: python grasp_quality.py file.hdf5 [--csv out.csv]"""
import sys, argparse, numpy as np, h5py
ap = argparse.ArgumentParser(); ap.add_argument("hdf5"); ap.add_argument("--csv"); a = ap.parse_args()
rows = []
with h5py.File(a.hdf5, "r") as f:
    for d in sorted(f["data"], key=lambda k: int(k.split("_")[1])):
        g = f["data"][d]; act = np.asarray(g["actions"]); eef = np.asarray(g["obs"]["eef_pos"]); toy = np.asarray(g["obs"]["toy_truck_positions"])
        grip = np.asarray(g["obs"]["gripper_pos"])[:, 0]
        close_cmd = act[:, 6] < 0   # gripper action: +1 open, -1 close (checked on the obs below)
        if not close_cmd.any(): continue
        t = int(np.argmax(close_cmd))                      # first close command
        d_xy = np.linalg.norm((eef[t, :2] - toy[t, :2]))   # hand-toy xy offset at close
        d_z = eef[t, 2] - toy[t, 2]
        speed = np.linalg.norm(eef[t] - eef[max(t-1, 0)])
        n_act_tog = int((np.diff(np.sign(act[:, 6])) != 0).sum())
        closed = grip > -0.6; closed[:3] = False
        n_obs_tog = int(np.abs(np.diff(closed.astype(int))).sum())
        lift = toy[:, 2] - toy[0, 2]
        lift_40 = float(lift[min(t + 40, len(lift) - 1)])   # toy height gain 40 steps (2 s) after the close
        # slip: hand-toy distance growth while the close command is on
        dh = np.linalg.norm(eef - toy, axis=1)
        on = close_cmd.copy(); on[:t] = False
        slip = float(dh[on].max() - dh[on].min()) if on.sum() > 5 else 0.0
        g_after = float(grip[min(t + 20, len(grip) - 1)])
        # fingers forced (nearly) open while the close command is held: reading below -0.75 after the first 5 steps
        win = on.copy(); win[:t + 5] = False
        rel = np.where(~close_cmd[t:])[0]
        if len(rel): win[t + rel[0]:] = False
        forced_open = int((grip[win] < -0.75).sum()) if win.any() else 0
        rows.append(dict(demo=d, grip_after=g_after, forced_open=forced_open, len=len(act), t_close=t, dxy_close=d_xy, dz_close=d_z, speed_close=speed, lift_2s=lift_40,
                         act_toggles=n_act_tog, obs_toggles=n_obs_tog, slip=slip, max_lift=float(lift.max())))
k = list(rows[0].keys())
A = {key: np.array([r[key] for r in rows]) for key in k if key != "demo"}
print(f"{a.hdf5}: {len(rows)} demos with a close command")
for key in ["grip_after", "t_close", "dxy_close", "dz_close", "speed_close", "lift_2s", "max_lift", "slip"]:
    v = A[key]; print(f"  {key:12s} mean {v.mean():.3f}  median {np.median(v):.3f}  p10 {np.percentile(v,10):.3f}  p90 {np.percentile(v,90):.3f}")
print(f"  dxy_close > 0.03: {(A['dxy_close']>0.03).mean():.0%}, > 0.05: {(A['dxy_close']>0.05).mean():.0%}")
print(f"  lift_2s < 0.02 (toy not lifted 2 s after the first close): {(A['lift_2s']<0.02).mean():.0%}")
print(f"  act_toggles > 2: {(A['act_toggles']>2).mean():.0%}; obs_toggles > 2: {(A['obs_toggles']>2).mean():.0%}; slip > 0.03: {(A['slip']>0.03).mean():.0%}")
print(f"  forced_open > 0 steps: {(A['forced_open']>0).mean():.0%}; > 5 steps: {(A['forced_open']>5).mean():.0%}")
clean = (A['act_toggles'] <= 2) & (A['lift_2s'] >= 0.02) & (A['forced_open'] <= 5)
print(f"  clean grasp (one close/open, toy lifted within 2 s of the close, fingers never forced open): {clean.sum()} ({clean.mean():.0%})")
if a.csv:
    open(a.csv.replace('.csv', '_clean.txt'), 'w').write("\n".join(r['demo'] for r, c in zip(rows, clean) if c) + "\n")
    open(a.csv.replace('.csv', '_dirty.txt'), 'w').write("\n".join(r['demo'] for r, c in zip(rows, clean) if not c) + "\n")
if a.csv:
    import csv
    with open(a.csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); [w.writerow(r) for r in rows]
    print("wrote", a.csv)
