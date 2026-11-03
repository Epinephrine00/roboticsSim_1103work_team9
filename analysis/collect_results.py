"""Collect the experiment numbers into analysis/results.json (cited in the notes and the report deck) and draw analysis/fig_experiment.png.
Conditions: clean162, dirty162, baseline (run names bc_rnn_<cond>_seed<seed>; baseline = bc_rnn_seed<seed>).
Official play.py logs: logs/experiments/<name>.play.log (baseline: the overnight scratchpad logs).
Fast eval outputs: next to each checkpoint (<stem>_eval.json, _stages.csv, _rollouts.npz).
Usage: python analysis/collect_results.py"""
import csv, glob, json, os, re, sys, numpy as np, matplotlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regrasp_analysis import analyse as regrasp_rows
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TASK = "Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0"
COND = {"clean162": "bc_rnn_clean162_seed{s}", "dirty162": "bc_rnn_dirty162_seed{s}", "baseline": "bc_rnn_seed{s}",
        "clean339": "bc_rnn_clean339_seed{s}", "random339": "bc_rnn_random339_seed{s}"}
PLAY_LOG = {"clean162": "logs/experiments/{name}.play.log", "dirty162": "logs/experiments/{name}.play.log",
            "clean339": "logs/experiments/{name}.play.log", "random339": "logs/experiments/{name}.play.log",
            "baseline": "logs/experiments/{name}.play.log"}
SEEDS = ["101", "111"]; STAGES = ["approach", "grasp", "carry", "place"]
BLUE, ORANGE, GRAY2, INK, INK2, GRID = "#2a78d6", "#eb6834", "#898781", "#0b0b0b", "#52514e", "#e1e0d9"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 160})

def ckpt_stem(name):
    c = sorted(glob.glob(f"logs/robomimic/{TASK}/{name}/*/models/model_epoch_2000.pth"))
    return c[-1][:-4] if c else None

def official(cond, seed, name):
    p = PLAY_LOG[cond][seed] if isinstance(PLAY_LOG[cond], dict) else PLAY_LOG[cond].format(name=name)
    if not os.path.exists(p): return None
    m = re.search(r"Successful trials:\s*(\d+),\s*out of\s*(\d+)", open(p, errors="ignore").read())
    return (int(m.group(1)), int(m.group(2))) if m else None

def fast(stem):
    if not stem or not os.path.exists(stem + "_eval.json") or not os.path.exists(stem + "_stages.csv"): return None
    j = json.load(open(stem + "_eval.json")); rows = list(csv.DictReader(open(stem + "_stages.csv")))
    roll = np.load(stem + "_rollouts.npz", allow_pickle=True)["rollouts"]
    flips = [int((np.diff(np.sign(r["actions"][:, 6])) != 0).sum()) for r in roll]
    res = [r["result"] for r in rows]
    rg = regrasp_rows(stem + "_rollouts.npz")
    reached = [r for r in rg if r["reached"] and r["n_close"] > 0]
    first_fail = [r for r in reached if r["first_ok"] is False]
    recovered = [r for r in first_fail if r["later_ok"]]
    return {"successes": j["successes"], "stages": {s: res.count(s) for s in STAGES}, "flips": flips, "results": res,
            "n_reached": len(reached), "n_first_ok": sum(1 for r in reached if r["first_ok"]), "n_first_fail": len(first_fail),
            "n_recovered": len(recovered), "n_recovered_success": sum(1 for r in recovered if r["success"]),
            "n_success_one_close": sum(1 for r in rg if r["success"] and r["n_close"] == 1)}

def mean_std(vals):  # population std over the two seeds (half the gap); stated as such in the report
    v = np.array(vals, float); return float(v.mean()), float(v.std())

out = {}; summary = {}
for cond, pat in COND.items():
    o = {}; f = {}
    for s in SEEDS:
        name = pat.format(s=s); o[s] = official(cond, s, name); f[s] = fast(ckpt_stem(name))
    entry = {"official": {}, "fast": {}}
    if all(o.values()):
        for s in SEEDS: entry["official"][s] = f"{o[s][0]} / {o[s][1]}"
        m, sd = mean_std([o[s][0] * 100 / o[s][1] for s in SEEDS]); entry["official"]["mean_std"] = f"{m:.1f} ± {sd:.1f} %"; entry["official"]["mean"] = m
    else:
        for s in SEEDS:
            if o[s]: entry["official"][s] = f"{o[s][0]} / {o[s][1]} (진행 중)"
    if all(f.values()):
        m, sd = mean_std([f[s]["successes"] for s in SEEDS]); entry["fast"]["mean_std"] = f"{m:.1f} ± {sd:.1f} %"; entry["fast"]["mean"] = m
        for s in SEEDS: entry["fast"][s] = f"{f[s]['successes']} / 100"
        fails = sum(100 - f[s]["successes"] for s in SEEDS)
        gc = sum(f[s]["stages"]["grasp"] + f[s]["stages"]["carry"] for s in SEEDS)
        entry["fast"]["grasp_carry_share"] = f"{gc / fails:.0%} ({gc}/{fails})" if fails else "-"
        entry["fast"]["stages"] = {st: sum(f[s]["stages"][st] for s in SEEDS) for st in STAGES}
        ff = [fl for s in SEEDS for fl, r in zip(f[s]["flips"], f[s]["results"]) if r != "success"]
        fs = [fl for s in SEEDS for fl, r in zip(f[s]["flips"], f[s]["results"]) if r == "success"]
        entry["fast"]["flips_fail_median"] = f"{np.median(ff):.0f}" if ff else "-"
        entry["fast"]["flips_success_median"] = f"{np.median(fs):.0f}" if fs else "-"
        entry["fast"]["flips_fail_ge4"] = f"{np.mean(np.array(ff) >= 4):.0%}" if ff else "-"
        fg = [fl for s in SEEDS for fl, r in zip(f[s]["flips"], f[s]["results"]) if r == "grasp"]
        entry["fast"]["flips_grasp_median"] = f"{np.median(fg):.0f}" if fg else "-"
        tot = lambda k: sum(f[s][k] for s in SEEDS)
        entry["fast"]["first_grasp_ok"] = f"{tot('n_first_ok')}/{tot('n_reached')} ({tot('n_first_ok')/max(tot('n_reached'),1):.0%})"
        entry["fast"]["recovery"] = f"{tot('n_recovered')}/{tot('n_first_fail')} ({tot('n_recovered')/max(tot('n_first_fail'),1):.0%})"
        entry["fast"]["success_via_recovery"] = f"{tot('n_recovered_success')}/{tot('successes')}"
        entry["fast"]["success_one_close"] = f"{tot('n_success_one_close')}/{tot('successes')}"
        summary[cond] = {"f": f, "ff": ff}
    out[cond] = entry

# verdict draft from the pre-registered criterion (only when both experiment conditions have fast evals; official preferred)
c, d = out.get("clean162", {}), out.get("dirty162", {})
bul = []
key = "official" if ("mean" in c.get("official", {}) and "mean" in d.get("official", {})) else "fast"
if "mean" in c.get(key, {}) and "mean" in d.get(key, {}):
    diff = c[key]["mean"] - d[key]["mean"]
    src = "공식 play.py" if key == "official" else "20 env 평가"
    bul.append(f"성공률({src}): clean162 {c[key]['mean_std']} vs dirty162 {d[key]['mean_std']} → 차이 {diff:+.1f} %p (기준 10 %p)")
    if "grasp_carry_share" in c["fast"]:
        bul.append(f"파지·운반 실패 비율: clean {c['fast']['grasp_carry_share']} vs dirty {d['fast']['grasp_carry_share']}")
        bul.append(f"실패 rollout의 그리퍼 전환 중앙값: clean {c['fast']['flips_fail_median']} vs dirty {d['fast']['flips_fail_median']} (4회 이상 {c['fast']['flips_fail_ge4']} vs {d['fast']['flips_fail_ge4']})")
        bul.append(f"첫 닫기로 2초 안에 든 비율: clean {c['fast']['first_grasp_ok']} vs dirty {d['fast']['first_grasp_ok']}")
        bul.append(f"첫 파지 실패 뒤 다시 닫아 들어 올린(회복) 비율: clean {c['fast']['recovery']} vs dirty {d['fast']['recovery']}; 회복을 거친 성공 {c['fast']['success_via_recovery']} vs {d['fast']['success_via_recovery']}")
    if "mean" in out.get("baseline", {}).get(key, {}):
        bul.append(f"참고: baseline 501개 {out['baseline'][key]['mean_std']}")
    out["result_bullets"] = bul
    out["verdict"] = ("(초안) 기준 충족 여부를 보고 적기: 성공률 차이 %+.1f %%p" % diff)
c3, r3 = out.get("clean339", {}), out.get("random339", {})
if "mean" in c3.get("fast", {}) and "mean" in r3.get("fast", {}):
    key3 = "official" if ("mean" in c3.get("official", {}) and "mean" in r3.get("official", {})) else "fast"
    src3 = "공식 play.py" if key3 == "official" else "20 env 평가"
    out["followup_bullets"] = [
        f"성공률({src3}): clean339 {c3[key3]['mean_std']} vs random339 {r3[key3]['mean_std']} → 차이 {c3[key3]['mean'] - r3[key3]['mean']:+.1f} %p",
        f"첫 닫기로 2초 안에 든 비율: clean {c3['fast']['first_grasp_ok']} vs random {r3['fast']['first_grasp_ok']}",
        f"첫 파지 실패 뒤 회복: clean {c3['fast']['recovery']} vs random {r3['fast']['recovery']}; 회복을 거친 성공 {c3['fast']['success_via_recovery']} vs {r3['fast']['success_via_recovery']}",
        f"파지 실패의 전환 중앙값: clean {c3['fast']['flips_grasp_median']} vs random {r3['fast']['flips_grasp_median']}",
    ]
    d3 = r3[key3]["mean"] - c3[key3]["mean"]
    if d3 >= 0:
        out["followup_verdict"] = (f"random339 {r3[key3]['mean_std']} ≥ clean339 {c3[key3]['mean_std']} (차이 {d3:+.1f} %p). "
                                   "시범 개수 339에서도 파지 품질 기준 선별은 성공률에 도움이 되지 않음. 실험 1의 결론 유지")
    else:
        out["followup_verdict"] = (f"clean339 {c3[key3]['mean_std']} > random339 {r3[key3]['mean_std']} (차이 {-d3:+.1f} %p). "
                                   "시범 개수 339에서는 선별이 유리. 실험 1의 결과는 개수 부족의 영향일 가능성")
    out["followup_bullets"].append("판정: " + out["followup_verdict"])
# hand-written verdict / insight text (analysis/results_text.json) overrides the drafts above
if os.path.exists("analysis/results_text.json"):
    out.update(json.load(open("analysis/results_text.json")))
json.dump(out, open("analysis/results.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

# figure: failure stages per condition (pooled over seeds) + flips of failed rollouts per condition
if summary:
    conds = [k for k in ["clean162", "dirty162", "baseline"] if k in summary]
    fig, (ax, ax2, ax3) = plt.subplots(1, 3, figsize=(10.4, 3.0), gridspec_kw={"width_ratios": [1.3, 0.9, 1.1]})
    w = 0.8 / len(conds); x = np.arange(len(STAGES)); cols = {"clean162": BLUE, "dirty162": ORANGE, "baseline": GRAY2}
    for k, cond in enumerate(conds):
        cnt = [out[cond]["fast"]["stages"][s] / 2 for s in STAGES]  # per 100 rollouts (mean of the 2 seeds)
        bars = ax.bar(x + (k - (len(conds) - 1) / 2) * w, cnt, width=w - 0.03, color=cols[cond], label=f"{cond} (success {out[cond]['fast']['mean']:.1f}/100)")
        for b, v in zip(bars, cnt): ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.0f}", ha="center", va="bottom", fontsize=8, color=INK2)
    ax.set_xticks(x); ax.set_xticklabels(STAGES); ax.set_ylabel("failed rollouts per 100 (mean of 2 seeds)"); ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
    ax.set_title("Failure stage by training condition (20-env eval)", fontsize=9.5)
    ax.set_ylim(0, max(out[c]["fast"]["stages"][s_] / 2 for c in conds for s_ in STAGES) * 1.5)  # headroom so the legend sits above the bars
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    rng = np.random.default_rng(0)
    for i, cond in enumerate(conds):
        v = np.clip(np.array(summary[cond]["ff"]), 0, 30)
        ax2.scatter(i + rng.uniform(-0.2, 0.2, len(v)), v, s=12, color=cols[cond], alpha=0.55, lw=0)
        ax2.hlines(np.median(v), i - 0.3, i + 0.3, color=INK, lw=1.6); ax2.text(i, 31.5, f"median {np.median(v):.0f}", ha="center", fontsize=8, color=INK2)
    ax2.set_xticks(range(len(conds))); ax2.set_xticklabels(conds); ax2.set_ylim(-1, 34); ax2.set_ylabel("gripper command sign changes\n(failed rollouts, clipped at 30)")
    ax2.yaxis.grid(True, color=GRID, lw=0.6); ax2.set_axisbelow(True); ax2.set_title("Gripper chattering of failed rollouts", fontsize=9.5)
    # third panel: first-grasp success, recovery after a failed first grasp, overall success (pooled over the 2 seeds)
    metrics = [("first close\nlifts the toy", "n_first_ok", "n_reached"), ("recovery after\nfailed first close", "n_recovered", "n_first_fail"), ("success\n(per 100)", "successes", None)]
    xm = np.arange(len(metrics))
    for k, cond in enumerate(conds):
        f2 = summary[cond]["f"]; vals = []
        for _, num, den in metrics:
            a = sum(f2[s][num] for s in SEEDS); b = sum(f2[s][den] for s in SEEDS) if den else 200
            vals.append(100 * a / max(b, 1))
        bars = ax3.bar(xm + (k - (len(conds) - 1) / 2) * w, vals, width=w - 0.03, color=cols[cond])
        for b, v in zip(bars, vals): ax3.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v:.0f}", ha="center", va="bottom", fontsize=8, color=INK2)
    ax3.set_xticks(xm); ax3.set_xticklabels([m[0] for m in metrics], fontsize=8.5); ax3.set_ylabel("%"); ax3.set_ylim(0, 65)
    ax3.yaxis.grid(True, color=GRID, lw=0.6); ax3.set_axisbelow(True); ax3.set_title("First grasp vs recovery (2 seeds pooled)", fontsize=9.5)
    fig.tight_layout(); fig.savefig("analysis/fig_experiment.png"); print("wrote analysis/fig_experiment.png")
    if "clean339" in summary and "random339" in summary:  # same 3 panels for the follow-up
        plt.close(fig)
        conds = ["clean339", "random339", "baseline"]; cols = {"clean339": BLUE, "random339": ORANGE, "baseline": GRAY2}
        fig, (ax, ax2, ax3) = plt.subplots(1, 3, figsize=(10.4, 3.0), gridspec_kw={"width_ratios": [1.3, 0.9, 1.1]})
        for k, cond in enumerate(conds):
            cnt = [out[cond]["fast"]["stages"][st] / 2 for st in STAGES]
            bars = ax.bar(x + (k - 1) * w, cnt, width=w - 0.03, color=cols[cond], label=f"{cond} (success {out[cond]['fast']['mean']:.1f}/100)")
            for b, v in zip(bars, cnt): ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.0f}", ha="center", va="bottom", fontsize=8, color=INK2)
        ax.set_xticks(x); ax.set_xticklabels(STAGES); ax.set_ylabel("failed rollouts per 100 (mean of 2 seeds)"); ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
        ax.set_title("Failure stage by training condition (20-env eval)", fontsize=9.5)
        ax.set_ylim(0, max(out[c]["fast"]["stages"][s_] / 2 for c in conds for s_ in STAGES) * 1.5)  # headroom so the legend sits above the bars
        ax.legend(loc="upper right", frameon=False, fontsize=8)
        for i, cond in enumerate(conds):
            v = np.clip(np.array(summary[cond]["ff"]), 0, 30)
            ax2.scatter(i + rng.uniform(-0.2, 0.2, len(v)), v, s=12, color=cols[cond], alpha=0.55, lw=0)
            ax2.hlines(np.median(v), i - 0.3, i + 0.3, color=INK, lw=1.6); ax2.text(i, 31.5, f"median {np.median(v):.0f}", ha="center", fontsize=8, color=INK2)
        ax2.set_xticks(range(3)); ax2.set_xticklabels(conds); ax2.set_ylim(-1, 34); ax2.set_ylabel("gripper command sign changes\n(failed rollouts, clipped at 30)")
        ax2.yaxis.grid(True, color=GRID, lw=0.6); ax2.set_axisbelow(True); ax2.set_title("Gripper chattering of failed rollouts", fontsize=9.5)
        for k, cond in enumerate(conds):
            f2 = summary[cond]["f"]; vals = []
            for _, num, den in metrics:
                a = sum(f2[s][num] for s in SEEDS); b = sum(f2[s][den] for s in SEEDS) if den else 200
                vals.append(100 * a / max(b, 1))
            bars = ax3.bar(xm + (k - 1) * w, vals, width=w - 0.03, color=cols[cond])
            for b, v in zip(bars, vals): ax3.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v:.0f}", ha="center", va="bottom", fontsize=8, color=INK2)
        ax3.set_xticks(xm); ax3.set_xticklabels([m[0] for m in metrics], fontsize=8.5); ax3.set_ylabel("%"); ax3.set_ylim(0, 65)
        ax3.yaxis.grid(True, color=GRID, lw=0.6); ax3.set_axisbelow(True); ax3.set_title("First grasp vs recovery (2 seeds pooled)", fontsize=9.5)
        fig.tight_layout(); fig.savefig("analysis/fig_followup.png"); print("wrote analysis/fig_followup.png")
