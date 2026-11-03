#!/bin/bash
# One controlled experiment: train every condition with seeds 101 and 111 (all runs in parallel, identical training
# settings from the official json: 2000 epochs x 100 gradient steps, batch 100), then the fast 20-env evaluation +
# failure-stage diagnosis (2 at a time), then the official play.py evaluation of every checkpoint (all in parallel).
#
# Usage: ./run_experiment.sh <tag>=<dataset.hdf5> [<tag>=<dataset.hdf5> ...]
#   e.g. ./run_experiment.sh clean162=datasets/mimic_clean162.hdf5 dirty162=datasets/mimic_dirty162.hdf5
# Env: SEEDS="101 111"   EXTRA="--override train.seq_length=20"  (extra train_bc_nokit.py args for every run)
# Runs are named bc_rnn_<tag>_seed<seed>; logs in ./logs/experiments/; checkpoints as usual under ./logs/robomimic/.
set -u
cd "$(dirname "$0")"
source "$HOME/miniforge3/etc/profile.d/conda.sh"; conda activate lerobot-arena
export OMNI_KIT_ACCEPT_EULA=YES PYTHONUNBUFFERED=1
TASK=Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0
SEEDS=${SEEDS:-"101 111"}
EXTRA=${EXTRA:-}
mkdir -p logs/experiments
log() { echo "[$(date +%F_%T)] $*"; }
ckpt_of() { ls -d logs/robomimic/$TASK/$1/*/models/model_epoch_2000.pth 2>/dev/null | tail -1; }
[ $# -ge 1 ] || { sed -n 2,10p "$0"; exit 1; }
names=()
for spec in "$@"; do
    tag=${spec%%=*}; ds=${spec#*=}
    [ -f "$ds" ] || { echo "missing dataset: $ds"; exit 1; }
    for seed in $SEEDS; do
        name=bc_rnn_${tag}_seed${seed}
        [ -d "logs/robomimic/$TASK/$name" ] && { echo "experiment dir already exists: $name"; exit 1; }
        names+=("$name")
    done
done
for spec in "$@"; do
    tag=${spec%%=*}; ds=${spec#*=}
    for seed in $SEEDS; do
        name=bc_rnn_${tag}_seed${seed}
        python train_bc_nokit.py --dataset "$ds" --name "$name" --seed "$seed" $EXTRA > "logs/experiments/$name.train.log" 2>&1 &
        log "train $name on $ds (pid $!)"
    done
done
wait
ckpts=()
for name in "${names[@]}"; do
    c=$(ckpt_of "$name")
    if [ -z "$c" ]; then log "no checkpoint for $name, see logs/experiments/$name.train.log"; continue; fi
    ckpts+=("$c"); log "trained $name -> $c"
done
[ ${#ckpts[@]} -ge 1 ] || { log "nothing to evaluate"; exit 1; }
log "fast evals + diagnosis (2 at a time)"
half=$(( (${#ckpts[@]} + 1) / 2 ))
./run_evals.sh "${ckpts[@]:0:$half}" > logs/experiments/fast_evals_a.log 2>&1 &
[ ${#ckpts[@]} -gt $half ] && ./run_evals.sh "${ckpts[@]:$half}" > logs/experiments/fast_evals_b.log 2>&1 &
wait
cat logs/experiments/fast_evals_a.log logs/experiments/fast_evals_b.log 2>/dev/null
log "official play.py evals (all in parallel)"
for c in "${ckpts[@]}"; do
    name=$(basename "$(dirname "$(dirname "$(dirname "$c")")")")
    ./isaaclab.sh -p scripts/imitation_learning/robomimic/play.py --task $TASK --checkpoint "$c" \
        --num_rollouts 100 --horizon 800 --seed 42 --headless > "logs/experiments/$name.play.log" 2>&1 &
done
wait
for c in "${ckpts[@]}"; do
    name=$(basename "$(dirname "$(dirname "$(dirname "$c")")")")
    log "$name official: $(grep -aE 'Successful trials' "logs/experiments/$name.play.log")"
done
log "EXPERIMENT DONE"
