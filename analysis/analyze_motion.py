"""Motion structure of demos: eef-speed dwell, axis-aligned moves, action levels. Usage: python analyze_motion.py file.hdf5 [...]"""
import sys, numpy as np, h5py
THR = 0.002   # m per step (20 Hz) below which the hand counts as stationary
for path in sys.argv[1:]:
    with h5py.File(path, "r") as f:
        demos = sorted(f["data"].keys(), key=lambda k: int(k.split("_")[1]))
        rows = []
        for d in demos:
            g = f["data"][d]
            eef = np.asarray(g["obs"]["eef_pos"])
            act = np.asarray(g["actions"])
            grip = np.asarray(g["obs"]["gripper_pos"])[:, 0]
            v = np.linalg.norm(np.diff(eef, axis=0), axis=1)
            still = v < THR
            # dwell segments (>= 10 consecutive stationary frames)
            segs = []; run = 0
            for s in still:
                run = run + 1 if s else 0
                if not s and run == 0:
                    pass
            runs = []; run = 0
            for s in still:
                if s: run += 1
                else:
                    if run >= 10: runs.append(run)
                    run = 0
            if run >= 10: runs.append(run)
            moving = ~still
            dv = np.abs(np.diff(eef, axis=0))[moving]
            axis_frac = (dv.max(1) / np.maximum(dv.sum(1), 1e-9) > 0.9).mean() if len(dv) else np.nan
            zero_act = (np.abs(act[:, :6]).max(1) < 1e-6).mean()
            closed = grip > -0.6; closed[:3] = False
            sw = int(np.abs(np.diff(closed.astype(int))).sum())
            rows.append((len(act), still.mean(), len(runs), sum(runs), axis_frac, zero_act, sw, v[moving].mean() if moving.any() else 0))
        r = np.array(rows, dtype=float)
        print(f"== {path}: {len(demos)} demos, mean len {r[:,0].mean():.0f}")
        print(f"  stationary frames (<{THR*1000:.0f} mm/step): {r[:,1].mean():.0%} of frames (per-demo min {r[:,1].min():.0%} max {r[:,1].max():.0%})")
        print(f"  dwell segments >=10 frames: {r[:,2].mean():.1f} per demo, {r[:,3].mean():.0f} frames per demo ({(r[:,3]/r[:,0]).mean():.0%})")
        print(f"  single-axis moves (one axis >90% of |d eef|): {np.nanmean(r[:,4]):.0%} of moving frames")
        print(f"  zero-action frames: {r[:,5].mean():.0%}; mean hand speed while moving: {r[:,7].mean()*1000:.1f} mm/step")
        print(f"  gripper switches: " + ", ".join(f"{int(k)}:{int(n)}" for k, n in zip(*np.unique(r[:,6], return_counts=True))))
        a = np.asarray(f["data"][demos[0]]["actions"])
        print(f"  first demo action levels per dim (unique values, first 3 dims): " + "; ".join(str(np.unique(np.round(a[:, i], 4))[:6]) for i in range(3)))
