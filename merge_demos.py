"""Merge several datasets recorded by record_demos.py into one file.

record_demos.py opens ``--dataset_file`` in write mode, so recording in several sittings
needs one file per sitting. This script concatenates them: episodes are renumbered demo_0,
demo_1, ... in input order and the ``total`` step count is recomputed. The ``data`` group
attributes (env_args, ...) are copied from the first input.

Usage:
    ./isaaclab.sh -p merge_demos.py --inputs ./datasets/part1.hdf5 ./datasets/part2.hdf5 \
        --output ./datasets/toy2box_agibot.hdf5
"""

import argparse
import json
import os

import h5py

parser = argparse.ArgumentParser(description="Merge record_demos.py HDF5 files.")
parser.add_argument("--inputs", nargs="+", required=True, help="Input HDF5 files, in the order to keep.")
parser.add_argument("--output", required=True, help="Output HDF5 file (must not exist unless --force).")
parser.add_argument("--force", action="store_true", help="Overwrite the output file if it exists.")
args = parser.parse_args()

if os.path.exists(args.output) and not args.force:
    raise SystemExit(f"[ERROR] {args.output} already exists. Choose another name or pass --force.")
for path in args.inputs:
    if os.path.abspath(path) == os.path.abspath(args.output):
        raise SystemExit("[ERROR] The output file cannot be one of the inputs.")


def demo_names(group):
    return sorted((n for n in group.keys() if n.startswith("demo_")), key=lambda n: int(n.split("_")[-1]))


with h5py.File(args.output, "w") as out:
    out_data = out.create_group("data")
    count = 0
    total = 0
    env_name = None
    for path in args.inputs:
        with h5py.File(path, "r") as src:
            data = src["data"]
            if count == 0:
                for key, value in data.attrs.items():
                    out_data.attrs[key] = value
            try:
                name = json.loads(data.attrs["env_args"]).get("env_name")
            except (KeyError, ValueError):
                name = None
            if env_name is None:
                env_name = name
            elif name != env_name:
                print(f"[WARN] {path}: env_name {name!r} differs from {env_name!r}")
            names = demo_names(data)
            for n in names:
                demo = data[n]
                if not bool(demo.attrs.get("success", True)):
                    print(f"[WARN] {path}/{n} is not marked successful; copied anyway")
                data.copy(demo, out_data, name=f"demo_{count}")
                total += int(demo.attrs.get("num_samples", len(demo["actions"])))
                count += 1
            print(f"{path}: {len(names)} episodes")
    out_data.attrs["total"] = total
print(f"-> {args.output}: {count} episodes | total: {total} steps")
