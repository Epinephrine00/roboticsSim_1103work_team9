"""Fast evaluation of a robomimic checkpoint with several environments at once, plus per-rollout logs for failure diagnosis.

Same rules as scripts/imitation_learning/robomimic/play.py (success term checked after every step, time_out disabled,
--horizon steps at most) but --num_envs rollouts run in lockstep. Each batch starts from env.reset() with the policy's
RNN state reset, so every rollout is an independent episode. The random numbers are consumed differently from play.py,
so use this for quick comparisons and the official play.py for the reported numbers.

Example:
    ./isaaclab.sh -p eval_multienv.py --checkpoint logs/robomimic/<task>/<name>/<time>/models/model_epoch_2000.pth \
        --num_envs 20 --num_rollouts 100 --horizon 800 --seed 42 --headless
Then:
    python diagnose_failures.py <same dir>/model_epoch_2000_rollouts.npz
"""

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Multi-env evaluation of a robomimic policy.")
parser.add_argument("--task", type=str, default="Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0")
parser.add_argument("--checkpoint", type=str, required=True, help="robomimic .pth checkpoint")
parser.add_argument("--num_envs", type=int, default=20, help="rollouts run in parallel")
parser.add_argument("--num_rollouts", type=int, default=100)
parser.add_argument("--horizon", type=int, default=800)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output", type=str, default=None, help="where to write <name>_rollouts.npz and <name>_eval.json (default: next to the checkpoint)")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import json
import os
import random
import time

import gymnasium as gym
import numpy as np
import torch

import robomimic.utils.file_utils as FileUtils
import robomimic.utils.obs_utils as ObsUtils
import robomimic.utils.tensor_utils as TensorUtils
import robomimic.utils.torch_utils as TorchUtils

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg

LOG_KEYS = ("eef_pos", "eef_quat", "gripper_pos", "toy_truck_positions", "toy_truck_orientations", "box_positions")


def main():
    n = args_cli.num_envs
    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=n)
    env_cfg.observations.policy.concatenate_terms = False
    env_cfg.terminations.time_out = None
    env_cfg.recorders = None
    success_term = env_cfg.terminations.success
    env_cfg.terminations.success = None
    env = gym.make(args_cli.task, cfg=env_cfg).unwrapped

    torch.manual_seed(args_cli.seed)
    np.random.seed(args_cli.seed)
    random.seed(args_cli.seed)
    env.seed(args_cli.seed)

    device = TorchUtils.get_torch_device(try_to_use_cuda=True)
    policy, _ = FileUtils.policy_from_checkpoint(ckpt_path=args_cli.checkpoint, device=device, verbose=False)
    algo = policy.policy
    obs_keys = list(algo.global_config.all_obs_keys)
    norm_stats = policy.obs_normalization_stats
    if norm_stats is not None:
        norm_stats = TensorUtils.to_float(TensorUtils.to_device(TensorUtils.to_tensor(norm_stats), device))

    def act(obs_policy):
        ob = {k: obs_policy[k].to(device).float() for k in obs_keys}
        if norm_stats is not None:
            ob = ObsUtils.normalize_obs(ob, obs_normalization_stats=norm_stats)
        return algo.get_action(obs_dict=ob)

    out_dir = args_cli.output or os.path.dirname(os.path.abspath(args_cli.checkpoint))
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args_cli.checkpoint))[0]

    rollouts = []  # one dict per rollout
    t_start = time.time()
    while len(rollouts) < args_cli.num_rollouts:
        n_use = min(n, args_cli.num_rollouts - len(rollouts))
        policy.start_episode()  # eval mode + RNN state reset for the whole batch
        obs_dict, _ = env.reset()
        success = torch.zeros(n, dtype=torch.bool, device=env.device)
        finished = torch.zeros(n, dtype=torch.bool, device=env.device)
        end_step = torch.full((n,), args_cli.horizon, dtype=torch.long, device=env.device)
        log = {k: [] for k in LOG_KEYS}
        log["actions"] = []
        for t in range(args_cli.horizon):
            obs = obs_dict["policy"]
            with torch.inference_mode():
                actions = act(obs)
            for k in LOG_KEYS:
                log[k].append(obs[k].detach().cpu().numpy())
            log["actions"].append(actions.detach().cpu().numpy())
            obs_dict, _, terminated, truncated, _ = env.step(actions.to(env.device).view(n, -1).clone())
            succ_now = success_term.func(env, **success_term.params).view(-1) & ~finished
            success |= succ_now
            end_step[succ_now] = t + 1
            finished |= succ_now
            # terminated envs (toy dropped) were reset inside env.step: freeze their result and ignore them from now on
            term_now = (terminated | truncated).view(-1) & ~finished
            end_step[term_now] = t + 1
            finished |= term_now
            if bool(finished[:n_use].all()):
                break
        stacked = {k: np.stack(v, axis=1) for k, v in log.items()}  # [n, T, dim]
        for i in range(n_use):
            e = int(end_step[i])
            rollouts.append({
                "success": bool(success[i]),
                "end_step": e,
                "dropped": bool(finished[i] and not success[i] and e < args_cli.horizon),
                **{k: stacked[k][i, :e].astype(np.float32) for k in stacked},
            })
        n_ok = sum(r["success"] for r in rollouts)
        print(f"[eval] {len(rollouts)}/{args_cli.num_rollouts} rollouts, {n_ok} successes so far ({time.time() - t_start:.0f}s)", flush=True)

    n_ok = sum(r["success"] for r in rollouts)
    rate = n_ok / len(rollouts)
    print(f"\nSuccessful trials: {n_ok}, out of {len(rollouts)} trials")
    print(f"Success rate: {rate}")
    summary = {
        "checkpoint": os.path.abspath(args_cli.checkpoint), "task": args_cli.task, "seed": args_cli.seed,
        "num_envs": n, "num_rollouts": len(rollouts), "horizon": args_cli.horizon,
        "successes": n_ok, "success_rate": rate,
        "per_rollout": [{"success": r["success"], "end_step": r["end_step"], "dropped": r["dropped"]} for r in rollouts],
        "elapsed_s": time.time() - t_start,
    }
    with open(os.path.join(out_dir, f"{stem}_eval.json"), "w") as f:
        json.dump(summary, f, indent=2)
    np.savez_compressed(os.path.join(out_dir, f"{stem}_rollouts.npz"), rollouts=np.array(rollouts, dtype=object))
    print(f"[eval] wrote {os.path.join(out_dir, stem + '_eval.json')} and {stem}_rollouts.npz")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
