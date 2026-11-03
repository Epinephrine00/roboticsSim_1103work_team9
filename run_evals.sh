#!/bin/bash
# Fast evaluation + failure-stage diagnosis for one or more checkpoints (same protocol as play.py: seed 42,
# 100 rollouts, horizon 800, but 20 envs in parallel). Outputs land next to each checkpoint:
#   <stem>_eval.json, <stem>_rollouts.npz, <stem>_diagnosis.txt, <stem>_stages.csv
# Usage: ./run_evals.sh <checkpoint.pth> [...]      (env: NUM_ENVS=20 ROLLOUTS=100 HORIZON=800 SEED=42)
set -u
cd "$(dirname "$0")"
export OMNI_KIT_ACCEPT_EULA=YES PYTHONUNBUFFERED=1
TASK=${TASK:-Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0}
for ckpt in "$@"; do
    dir=$(dirname "$ckpt"); stem=$(basename "${ckpt%.pth}")
    echo "[$(date +%T)] eval $ckpt"
    ./isaaclab.sh -p eval_multienv.py --task "$TASK" --checkpoint "$ckpt" --num_envs "${NUM_ENVS:-20}" \
        --num_rollouts "${ROLLOUTS:-100}" --horizon "${HORIZON:-800}" --seed "${SEED:-42}" --headless > "$dir/${stem}_eval.log" 2>&1
    if [ ! -f "$dir/${stem}_rollouts.npz" ]; then echo "  eval FAILED, see $dir/${stem}_eval.log"; continue; fi
    grep -E 'Successful trials|Success rate' "$dir/${stem}_eval.log" | sed 's/^/  /'
    python diagnose_failures.py "$dir/${stem}_rollouts.npz" --csv "$dir/${stem}_stages.csv" > "$dir/${stem}_diagnosis.txt" 2>&1
    head -8 "$dir/${stem}_diagnosis.txt" | sed "s/^/  /"
done
echo "[$(date +%T)] evals done"
