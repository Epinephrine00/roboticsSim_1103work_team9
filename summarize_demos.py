"""Summarize a recorded demonstration dataset (length, gripper switches, idle ratio, success flag).

Usage:
    ./isaaclab.sh -p summarize_demos.py [--dataset_file ./datasets/toy2box_agibot.hdf5]

Columns:
    len   steps in the demo; in parentheses the duration at the env step rate (20 Hz here)
    sw    number of gripper command switches (open <-> close)
    idle  share of steps with no arm motion command (no key held)
    ok    success flag stored in the HDF5 (record_demos.py only exports successful demos)
"""

import argparse
import json

import h5py
import numpy as np

parser = argparse.ArgumentParser(description="Summarize a recorded demonstration dataset.")
parser.add_argument("--dataset_file", default="./datasets/toy2box_agibot.hdf5", help="HDF5 file from record_demos.py.")
args = parser.parse_args()


def step_hz(data_group) -> float:
    try:
        env_args = json.loads(data_group.attrs["env_args"])
        return 1.0 / (env_args["sim_args"]["dt"] * env_args["decimation"])
    except (KeyError, TypeError, ValueError):
        return 20.0


with h5py.File(args.dataset_file, "r") as f:
    data = f["data"]
    hz = step_hz(data)
    names = sorted(data.keys(), key=lambda n: int(n.split("_")[-1]))
    total = sum(len(data[n]["actions"]) for n in names)
    print(f"episodes: {len(names)} | total: {total}")
    for name in names:
        demo = data[name]
        actions = np.asarray(demo["actions"])
        gripper = np.sign(actions[:, -1])
        switches = int(np.count_nonzero(np.diff(gripper)))
        idle = float(np.mean(np.all(np.abs(actions[:, :-1]) < 1e-6, axis=1)))
        ok = int(bool(demo.attrs.get("success", False)))
        print(f"{name:<14} len={len(actions):4d} ({len(actions) / hz:.1f}s) sw={switches:2d} idle={idle:.0%} ok={ok}")
