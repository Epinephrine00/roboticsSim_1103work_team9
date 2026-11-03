#!/bin/bash
# Follow-up: clean339 vs random339, same training settings, 2 trainings at a time (GPU memory budget).
cd /home/dpvpd/IsaacLab_RS
source "$HOME/miniforge3/etc/profile.d/conda.sh"; conda activate lerobot-arena
export PYTHONUNBUFFERED=1
log() { echo "[$(date +%F_%T)] $*"; }
for seed in 101 111; do
    for tag in clean339 random339; do
        name=bc_rnn_${tag}_seed${seed}
        python train_bc_nokit.py --dataset datasets/mimic_${tag}.hdf5 --name $name --seed $seed > logs/experiments/$name.train.log 2>&1 &
        log "train $name (pid $!)"
    done
    wait
    log "seed $seed pair finished"
done
log "FOLLOWUP TRAIN DONE"
