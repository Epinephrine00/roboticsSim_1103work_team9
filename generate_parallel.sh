#!/bin/bash
# Mimic data generation split over several processes (RMPFlow runs per env on one CPU core, so one process cannot use
# the other cores). Each process gets its own seed and output part; the parts are merged at the end.
#
# Usage: ./generate_parallel.sh <processes> <envs per process> <total successes wanted> <annotated input.hdf5> <output.hdf5>
#   e.g. ./generate_parallel.sh 4 25 500 ./datasets/toy2box_all_annotated.hdf5 ./datasets/toy2box_all_mimic_p4_500.hdf5
# The parts (<output>_part1.hdf5 ...) and their logs are kept next to the output; the failed-demo files are for analysis only.
set -u
if [ $# -lt 5 ]; then sed -n 2,9p "$0"; exit 1; fi
NP=$1; NE=$2; TOTAL=$3; IN=$4; OUT=$5; shift 5
TASK=${TASK:-Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-Rel-Mimic-v0}
cd "$(dirname "$0")"
export OMNI_KIT_ACCEPT_EULA=YES PYTHONUNBUFFERED=1
[ -e "$OUT" ] && { echo "refusing to overwrite $OUT"; exit 1; }
per=$(( (TOTAL + NP - 1) / NP ))
base=${OUT%.hdf5}
pids=(); parts=()
echo "[$(date +%T)] $NP generators x $NE envs, $per successes each -> $OUT"
count_demos() {  # prints the number of demos in an HDF5 file, or -1 if it cannot be read
    python - "$1" <<'PY'
import sys
try:
    import h5py
    with h5py.File(sys.argv[1], "r") as f:
        print(len(f["data"]))
except Exception:
    print(-1)
PY
}
for i in $(seq 1 "$NP"); do
    part="${base}_part${i}.hdf5"; parts+=("$part")
    [ "$i" -gt 1 ] && sleep "${STAGGER:-15}"   # spread the simulator start-up load (the RMPFlow file download is serialized by generate_seeded.py)
    ./isaaclab.sh -p generate_seeded.py --seed "$i" -- --task "$TASK" --headless --num_envs "$NE" \
        --generation_num_trials "$per" --input_file "$IN" --output_file "$part" "$@" > "${base}_part${i}.log" 2>&1 &
    pids+=($!)
done
fail=0
for i in "${!pids[@]}"; do
    wait "${pids[$i]}"   # isaaclab.sh does not pass the python exit code through, so check the output instead
    n=$(count_demos "${parts[$i]}")
    if [ "$n" -lt 1 ] || grep -q "Traceback" "${base}_part$((i+1)).log"; then
        echo "generator $((i+1)) failed ($n demos), see ${base}_part$((i+1)).log"; fail=1
    else
        echo "  part$((i+1)): $n demos; $(grep -E 'successful demos generated' "${base}_part$((i+1)).log" | tail -1 | tr -d '\033[K')"
    fi
done
[ $fail -eq 0 ] || exit 1
./isaaclab.sh -p scripts/tools/merge_hdf5_datasets.py --input_files "${parts[@]}" --output_file "$OUT" > "${base}_merge.log" 2>&1
n=$(count_demos "$OUT")
[ "$n" -ge 1 ] || { echo "merge failed, see ${base}_merge.log"; exit 1; }
echo "[$(date +%T)] merged $n demos -> $OUT"
