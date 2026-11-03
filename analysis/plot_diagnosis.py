"""Baseline diagnosis figures for the Toy2Box BC report (English labels; plain style).
Usage: python analysis/plot_diagnosis.py  (paths are hard-coded below)"""
import csv, numpy as np, h5py, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.titlecolor": INK, "axes.titlesize": 11,
                     "figure.facecolor": "white", "axes.facecolor": "white", "savefig.dpi": 160})
D = "logs/robomimic/Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0"
RUNS = {"seed 101": f"{D}/bc_rnn_seed101/20261103055223/models/model_epoch_2000",
        "seed 111": f"{D}/bc_rnn_seed111/20261103055312/models/model_epoch_2000"}
STAGES = ["approach", "grasp", "carry", "place"]

def act_flips(r):
    a = r["actions"][:, 6]
    return int((np.diff(np.sign(a)) != 0).sum())

def obs_flips(r):
    closed = r["gripper_pos"][:, 0] > -0.6; closed[:3] = False
    return int((np.diff(closed.astype(int)) != 0).sum())

rows = {}
for name, base in RUNS.items():
    stages = {int(r["rollout"]): r for r in csv.DictReader(open(base + "_stages.csv"))}
    roll = np.load(base + "_rollouts.npz", allow_pickle=True)["rollouts"]
    rows[name] = [dict(result=stages[i]["result"], act=act_flips(r), obs=obs_flips(r), r=r) for i, r in enumerate(roll)]

# ---- table of flips per outcome (printed, for the notes)
print("gripper flips per outcome (median act-sign flips / median obs toggles / n, pooled and per seed)")
for res in ["success"] + STAGES:
    line = f"{res:9s}"
    for name in list(RUNS) + ["pooled"]:
        rr = [x for n2 in (RUNS if name == "pooled" else [name]) for x in rows[n2] if x["result"] == res]
        if rr:
            a = np.array([x["act"] for x in rr]); o = np.array([x["obs"] for x in rr])
            line += f" | {name}: act {np.median(a):4.1f} (>=4: {(a>=4).mean():3.0%}) obs {np.median(o):4.1f} n={len(rr):3d}"
    print(line)

# ---- fig 1: failure stages per seed
fig, ax = plt.subplots(figsize=(5.2, 3.0))
w = 0.36; x = np.arange(len(STAGES))
for k, (name, col) in enumerate(zip(RUNS, [BLUE, ORANGE])):
    cnt = [sum(r["result"] == s for r in rows[name]) for s in STAGES]
    bars = ax.bar(x + (k - 0.5) * w, cnt, width=w - 0.04, color=col, label=f"{name} (success {sum(r['result']=='success' for r in rows[name])}/100)")
    for b, c in zip(bars, cnt):
        ax.text(b.get_x() + b.get_width() / 2, c + 0.4, str(c), ha="center", va="bottom", fontsize=9, color=INK2)
ax.set_xticks(x); ax.set_xticklabels(["approach\n(hand never\nreaches toy)", "grasp\n(not lifted)", "carry\n(lifted, never\nnear box)", "place\n(near box,\nnot placed)"])
ax.set_ylabel("failed rollouts (of 100)"); ax.set_ylim(0, 32); ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.set_title("Baseline BC-RNN (500 Mimic demos): failure stage of 100 rollouts", fontsize=10); ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig("analysis/fig_baseline_stages.png"); plt.close(fig)

# ---- fig 2: gripper command sign flips per outcome (pooled over both seeds)
fig, ax = plt.subplots(figsize=(5.2, 3.0))
cats = ["success"] + STAGES; rng = np.random.default_rng(0)
for i, res in enumerate(cats):
    v = np.array([x["act"] for n in RUNS for x in rows[n] if x["result"] == res])
    v = np.clip(v, 0, 30)
    ax.scatter(i + rng.uniform(-0.18, 0.18, len(v)), v, s=14, color=BLUE if res == "success" else ORANGE, alpha=0.55, lw=0)
    ax.hlines(np.median(v), i - 0.28, i + 0.28, color=INK, lw=1.6)
    ax.text(i, 31.5, f"median {np.median(v):.0f}", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(range(len(cats))); ax.set_xticklabels([f"{c}\n(n={sum(1 for n in RUNS for x in rows[n] if x['result']==c)})" for c in cats])
ax.set_ylabel("gripper command sign changes\nper rollout (clipped at 30)"); ax.set_ylim(-1, 34); ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.set_title("Gripper command sign changes per rollout, by outcome (200 rollouts)", fontsize=9.5)
fig.tight_layout(); fig.savefig("analysis/fig_grip_switches.png"); plt.close(fig)

# ---- fig 3: example rollouts, success vs chattering carry failure (seed 101)
def pick(name, res, many):
    cand = [x for x in rows[name] if x["result"] == res]
    cand.sort(key=lambda x: x["act"], reverse=many)
    return cand[len(cand) // 2 if not many else 0]
ex = [("success", pick("seed 101", "success", False)), ("carry failure", pick("seed 101", "carry", True))]
fig, axes = plt.subplots(3, 2, figsize=(7.2, 4.6), sharex="col")
for c, (title, x) in enumerate(ex):
    r = x["r"]; T = np.arange(len(r["actions"])) / 20.0
    axes[0, c].step(T, r["actions"][:, 6], where="post", color=BLUE, lw=1.2); axes[0, c].set_ylim(-1.3, 1.3); axes[0, c].set_yticks([-1, 1]); axes[0, c].set_yticklabels(["close", "open"])
    axes[0, c].set_title(f"{title}: {x['act']} gripper command sign changes", fontsize=9)
    axes[1, c].plot(T, r["gripper_pos"][:, 0], color=ORANGE, lw=1.2); axes[1, c].set_ylim(-1.05, 0.05)
    axes[2, c].plot(T, r["toy_truck_positions"][:, 2] - r["toy_truck_positions"][0, 2], color=AQUA, lw=1.2); axes[2, c].set_ylim(-0.05, 0.7)
    axes[2, c].set_xlabel("time [s]")
    for a in axes[:, c]: a.yaxis.grid(True, color=GRID, lw=0.6); a.set_axisbelow(True)
axes[0, 0].set_ylabel("gripper\ncommand"); axes[1, 0].set_ylabel("gripper_pos\nobservation"); axes[2, 0].set_ylabel("toy height\ngain [m]")
fig.tight_layout(); fig.savefig("analysis/fig_rollout_examples.png"); plt.close(fig)

# ---- fig 4: Mimic demo grasp quality (criteria counts) + example clean/dirty demo
q = list(csv.DictReader(open("analysis/mimic500_grasp.csv")))
A = {k: np.array([float(r[k]) for r in q]) for k in q[0] if k != "demo"}
crit = {"second close\n(act toggles > 2)": A["act_toggles"] > 2, "toy not lifted\n2 s after close": A["lift_2s"] < 0.02, "fingers forced open\n(> 5 steps)": A["forced_open"] > 5}
dirty = np.zeros(len(q), bool)
for v in crit.values(): dirty |= v
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw={"width_ratios": [1.0, 1.4]})
labels = list(crit) + ["any of these\n(dirty grasp)", "none\n(clean grasp)"]
vals = [v.sum() for v in crit.values()] + [dirty.sum(), (~dirty).sum()]
cols = [ORANGE] * 3 + [ORANGE, BLUE]
b = ax.barh(np.arange(len(labels))[::-1], vals, color=cols, height=0.62)
for bb, v in zip(b, vals): ax.text(v + 4, bb.get_y() + bb.get_height() / 2, f"{v} ({v/len(q):.0%})", va="center", fontsize=9, color=INK2)
ax.set_yticks(np.arange(len(labels))[::-1]); ax.set_yticklabels(labels, fontsize=8.5); ax.set_xlim(0, 420); ax.set_xlabel(f"Mimic demos (of {len(q)})")
ax.xaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True); ax.set_title("Grasp quality of 501 Mimic demos", fontsize=9.5)
# example traces
clean_names = [l.strip() for l in open("analysis/mimic500_grasp_clean.txt") if l.strip()]
dirty_rows = sorted([r for r in q if r["demo"] not in set(clean_names)], key=lambda r: -float(r["act_toggles"]))
with h5py.File("datasets/toy2box_all_mimic_v1_500.hdf5", "r") as f:
    for name, col, lab in [(clean_names[0], BLUE, "clean"), (dirty_rows[len(dirty_rows)//6]["demo"], ORANGE, "dirty")]:
        g = f["data"][name]; act = np.asarray(g["actions"])[:, 6]; grip = np.asarray(g["obs"]["gripper_pos"])[:, 0]; T = np.arange(len(act)) / 20.0
        ax2.step(T, act, where="post", color=col, lw=1.2, label=f"{lab} demo ({name}): gripper command")
        ax2.plot(T, grip * 0 + grip, color=col, lw=0.9, ls=":", alpha=0.9)
ax2.set_ylim(-1.3, 1.3); ax2.set_yticks([-1, 0, 1]); ax2.set_yticklabels(["close / -1", "0", "open / +1"], fontsize=8); ax2.set_xlabel("time [s]"); ax2.set_title("Example demos (solid: command, dotted: obs)", fontsize=9)
ax2.legend(frameon=False, fontsize=8, loc="center left", bbox_to_anchor=(0.0, 0.58)); ax2.yaxis.grid(True, color=GRID, lw=0.6); ax2.set_axisbelow(True)
fig.tight_layout(); fig.savefig("analysis/fig_demo_quality.png"); plt.close(fig)
print("wrote analysis/fig_baseline_stages.png fig_grip_switches.png fig_rollout_examples.png fig_demo_quality.png")
