"""Write a subset of a robomimic/Isaac Lab HDF5 dataset to a new file (demos renumbered demo_0..N-1, attrs kept).

Usage:
  python subset_hdf5.py --input in.hdf5 --output out.hdf5 --demos demo_3 demo_7 ...        # explicit list
  python subset_hdf5.py --input in.hdf5 --output out.hdf5 --list names.txt                # one demo name per line
  python subset_hdf5.py --input in.hdf5 --output out.hdf5 --random 146 --seed 0           # random subset
  python subset_hdf5.py --input in.hdf5 --output out.hdf5 --list clean.txt --random 146 --seed 0   # random N of the list
"""
import argparse, os, random, h5py

p = argparse.ArgumentParser()
p.add_argument("--input", required=True); p.add_argument("--output", required=True)
p.add_argument("--demos", nargs="*", default=None); p.add_argument("--list", default=None)
p.add_argument("--random", type=int, default=None, help="pick this many demos at random (from --list/--demos if given, else from all)")
p.add_argument("--seed", type=int, default=0)
a = p.parse_args()
if os.path.exists(a.output):
    raise SystemExit(f"refusing to overwrite {a.output}")
with h5py.File(a.input, "r") as src:
    names = a.demos or ([l.strip() for l in open(a.list) if l.strip()] if a.list else sorted(src["data"], key=lambda k: int(k.split("_")[1])))
    missing = [n for n in names if n not in src["data"]]
    if missing:
        raise SystemExit(f"not in {a.input}: {missing[:5]}")
    if a.random is not None:
        rng = random.Random(a.seed); names = sorted(rng.sample(names, a.random), key=lambda k: int(k.split("_")[1]))
    with h5py.File(a.output, "w") as dst:
        for k, v in src.attrs.items(): dst.attrs[k] = v
        data = dst.create_group("data")
        for k, v in src["data"].attrs.items(): data.attrs[k] = v
        total = 0
        for i, n in enumerate(names):
            src["data"].copy(n, data, name=f"demo_{i}")
            total += int(src["data"][n].attrs.get("num_samples", len(src["data"][n]["actions"])))
        data.attrs["total"] = total
        if "mask" in src:
            src.copy("mask", dst)  # filter keys are copied as-is; they refer to the old demo names
    with open(a.output + ".demos.txt", "w") as f:
        f.write("\n".join(f"demo_{i}\t{n}" for i, n in enumerate(names)) + "\n")
print(f"wrote {a.output}: {len(names)} demos, {total} steps (source names in {a.output}.demos.txt)")
