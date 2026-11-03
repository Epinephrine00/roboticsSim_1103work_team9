#!/bin/bash
# Copy the two final checkpoints (seeds 101 and 111) of one training condition into ./checkpoints/ and write
# play_command.txt in the Week 8 slide-44/48 format.  Usage: ./prepare_submission.sh <run_name_seed101> <run_name_seed111>
#   e.g. ./prepare_submission.sh bc_rnn_clean162_seed101 bc_rnn_clean162_seed111
set -eu
cd "$(dirname "$0")"
TASK=Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0
[ $# -eq 2 ] || { sed -n 2,4p "$0"; exit 1; }
mkdir -p checkpoints
: > play_command.txt
for name in "$@"; do
    src=$(ls -d logs/robomimic/$TASK/$name/*/models/model_epoch_2000.pth | tail -1)
    [ -f "$src" ] || { echo "no checkpoint for $name"; exit 1; }
    dst=checkpoints/$name/model_epoch_2000.pth
    mkdir -p "$(dirname "$dst")"; cp "$src" "$dst"
    cp "$(dirname "$src")/../config.json" "checkpoints/$name/config.json" 2>/dev/null || true
    echo "$dst  ($(du -h "$dst" | cut -f1))"
    cat >> play_command.txt <<CMD
# $name (train seed ${name##*seed}, epoch 2000)
./isaaclab.sh -p scripts/imitation_learning/robomimic/play.py --task $TASK --checkpoint ./$dst --num_rollouts 100 --horizon 800 --seed 42 --headless

CMD
done
echo "wrote play_command.txt:"; cat play_command.txt
