#!/bin/bash
# Follow-up experiment finisher (detached): as soon as each seed pair of clean339/random339 is trained, run the
# 20-env evaluation + diagnosis (2 at a time), then rebuild results.json and the report deck.
cd /home/dpvpd/IsaacLab_RS
source "$HOME/miniforge3/etc/profile.d/conda.sh"; conda activate lerobot-arena
export OMNI_KIT_ACCEPT_EULA=YES PYTHONUNBUFFERED=1
T=logs/robomimic/Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0
log() { echo "[$(date +%F_%T)] $*"; }
ckpt() { ls $T/$1/*/models/model_epoch_2000.pth 2>/dev/null | tail -1; }
for seed in 101 111; do
    a=bc_rnn_clean339_seed$seed; b=bc_rnn_random339_seed$seed
    until [ -n "$(ckpt $a)" ] && [ -n "$(ckpt $b)" ]; do sleep 60; done
    log "seed $seed pair trained -> fast evals"
    ./run_evals.sh "$(ckpt $a)" > logs/experiments/fast_eval_$a.log 2>&1 &
    ./run_evals.sh "$(ckpt $b)" > logs/experiments/fast_eval_$b.log 2>&1 &
    wait
    grep -ahE 'Successful trials' logs/experiments/fast_eval_$a.log logs/experiments/fast_eval_$b.log | sed "s/^/  /"
    log "seed $seed pair evaluated"
done
python analysis/collect_results.py > logs/experiments/collect_results_final.log 2>&1 && log "results.json rebuilt" || log "collect_results FAILED"
[ -f analysis/make_report_deck.py ] && { python analysis/make_report_deck.py > logs/experiments/make_report_deck_final.log 2>&1 && log "report deck rebuilt" || log "make_report_deck FAILED"; }
python analysis/make_deck.py > /dev/null 2>&1 && log "old-style deck rebuilt"
log "FOLLOWUP EVAL DONE"
