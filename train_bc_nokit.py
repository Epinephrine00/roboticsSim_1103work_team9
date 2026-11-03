"""Train a robomimic policy with the official Isaac Lab training code, without starting Isaac Sim.

scripts/imitation_learning/robomimic/train.py launches the Kit app (about 1 GB of GPU memory and a slow start)
although BC training never touches the simulator. This wrapper loads that file with the AppLauncher lines and
the isaaclab_tasks imports removed and runs its train() unchanged, so the training itself is identical.

Usage (conda env active, from the repo root):
  python train_bc_nokit.py --config <robomimic json> --dataset <hdf5> --name <experiment name> [--seed 101]
                           [--epochs 2000] [--log_dir robomimic] [--task <task name for the log folder>]
                           [--override train.seq_length=20 --override algo.rnn.horizon=20 ...]
Checkpoints land in ./logs/<log_dir>/<task>/<name>/<timestamp>/models/, exactly like the official script.
"""
import argparse
import json
import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
OFFICIAL = os.path.join(HERE, "scripts", "imitation_learning", "robomimic", "train.py")
DEFAULT_CONFIG = os.path.join(
    HERE, "source", "isaaclab_tasks", "isaaclab_tasks", "manager_based", "manipulation", "place", "config", "agibot",
    "agents", "robomimic", "bc_rnn_low_dim.json")
DEFAULT_TASK = "Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0"


def load_official_without_kit():
    src = open(OFFICIAL).read()
    stripped = re.sub(r"^(from isaaclab\.app import AppLauncher|app_launcher = .*|simulation_app = .*|import isaaclab_tasks.*)$",
                      "", src, flags=re.M)
    assert "AppLauncher(" not in stripped and "isaaclab_tasks" not in stripped, "unexpected train.py layout"
    mod = types.ModuleType("isaaclab_robomimic_train")
    mod.__file__ = OFFICIAL
    exec(compile(stripped, OFFICIAL, "exec"), mod.__dict__)
    return mod


def set_nested(d, dotted, value):
    keys = dotted.split(".")
    for k in keys[:-1]:
        d = d[k]
    if keys[-1] not in d:
        raise KeyError(f"unknown config key: {dotted}")
    d[keys[-1]] = value


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default=DEFAULT_CONFIG, help="robomimic json config (default: the agibot bc_rnn_low_dim.json)")
    p.add_argument("--dataset", required=True)
    p.add_argument("--name", required=True, help="experiment name (must not exist yet under the log folder)")
    p.add_argument("--seed", type=int, default=None, help="overrides train.seed from the json")
    p.add_argument("--epochs", type=int, default=None)
    p.add_argument("--log_dir", default="robomimic")
    p.add_argument("--task", default=DEFAULT_TASK, help="only used for the log folder name, as in the official script")
    p.add_argument("--override", action="append", default=[], metavar="KEY=JSON",
                   help="extra config override, e.g. train.seq_length=20 (value parsed as JSON)")
    args = p.parse_args()

    mod = load_official_without_kit()
    ext_cfg = json.load(open(args.config))
    if args.seed is not None:
        ext_cfg["train"]["seed"] = args.seed
    for ov in args.override:
        key, _, val = ov.partition("=")
        set_nested(ext_cfg, key.strip(), json.loads(val))
    config = mod.config_factory(ext_cfg["algo_name"])
    with config.values_unlocked():
        config.update(ext_cfg)
    config.train.data = args.dataset
    config.experiment.name = args.name
    if args.epochs is not None:
        config.train.num_epochs = args.epochs
    config.train.output_dir = os.path.abspath(os.path.join("./logs", args.log_dir, args.task))
    log_dir, ckpt_dir, video_dir = mod.TrainUtils.get_exp_dir(config)
    device = mod.TorchUtils.get_torch_device(try_to_use_cuda=config.train.cuda)
    config.lock()
    print(f"[train_bc_nokit] seed={config.train.seed} epochs={config.train.num_epochs} dataset={args.dataset}")
    print(f"[train_bc_nokit] overrides={args.override}")
    res_str = "finished run successfully!"
    try:
        mod.train(config, device, log_dir, ckpt_dir, video_dir)
    except Exception as e:
        import traceback
        res_str = f"run failed with error:\n{e}\n\n{traceback.format_exc()}"
    print(res_str)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
