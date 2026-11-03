"""Grasp attempts and recovery in evaluation rollouts (eval_multienv.py *_rollouts.npz).
For every rollout: number of close-command segments, whether the FIRST close lifted the toy within 2 s (40 steps),
whether a LATER close did (recovery), and the outcome.  Usage: python analysis/regrasp_analysis.py <label>=<npz> ..."""
import sys, numpy as np

def segments(close):  # start indices of close-command segments
    d = np.diff(np.concatenate([[0], close.astype(int)]))
    return np.where(d == 1)[0]

def analyse(npz):
    roll = np.load(npz, allow_pickle=True)["rollouts"]
    rows = []
    for r in roll:
        act = r["actions"][:, 6]; toy = r["toy_truck_positions"]; eef = r["eef_pos"]
        close = act < 0; lift = toy[:, 2] - toy[0, 2]
        starts = segments(close)
        d_hand = np.linalg.norm(eef - toy, axis=1)
        reached = bool(d_hand.min() < 0.08)
        first_ok = later_ok = None
        if len(starts):
            t0 = starts[0]; first_ok = bool(lift[t0:min(t0 + 40, len(lift))].max() > 0.02)
            later_ok = any(bool(lift[t:min(t + 40, len(lift))].max() > 0.02) for t in starts[1:])
        rows.append(dict(success=bool(r["success"]), reached=reached, n_close=len(starts), first_ok=first_ok, later_ok=later_ok,
                         lifted=bool(lift.max() > 0.05), steps=int(r["end_step"])))
    return rows

for spec in sys.argv[1:]:
    label, npz = spec.split("=", 1); rows = analyse(npz); n = len(rows)
    succ = [r for r in rows if r["success"]]
    reached = [r for r in rows if r["reached"] and r["n_close"] > 0]
    first_fail = [r for r in reached if r["first_ok"] is False]
    recovered = [r for r in first_fail if r["later_ok"]]
    rec_succ = [r for r in recovered if r["success"]]
    one_close_succ = [r for r in succ if r["n_close"] == 1]
    print(f"== {label}: {n} rollouts, success {len(succ)}")
    print(f"  reached toy and closed at least once: {len(reached)}")
    print(f"  first close lifted the toy within 2 s: {sum(1 for r in reached if r['first_ok'])} ({sum(1 for r in reached if r['first_ok'])/max(len(reached),1):.0%} of reached)")
    print(f"  first close failed: {len(first_fail)} -> re-closed and lifted later (recovery): {len(recovered)} ({len(recovered)/max(len(first_fail),1):.0%}), of which success: {len(rec_succ)}")
    print(f"  successes with exactly one close segment: {len(one_close_succ)}/{len(succ)}; median close segments: success {np.median([r['n_close'] for r in succ]) if succ else '-'}, failure {np.median([r['n_close'] for r in rows if not r['success']]):.0f}")
