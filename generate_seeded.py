"""Run the official generate_dataset.py with a chosen Mimic data-generation seed.

generate_dataset.py has no --seed option: the seed is fixed in the Mimic env config (datagen_config.seed = 1), so two
runs produce the same demos. This wrapper patches that one value, serializes the RMPFlow file download between
processes (a file lock), and otherwise runs the official script unchanged.
generate_parallel.sh uses it to run several generators at once with different seeds.

    ./isaaclab.sh -p generate_seeded.py --seed 2 -- --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-Rel-Mimic-v0 \
        --headless --num_envs 25 --generation_num_trials 125 --input_file <annotated.hdf5> --output_file <part2.hdf5>
"""

import os
import runpy
import sys

args = sys.argv[1:]
seed = None
if "--seed" in args:
    i = args.index("--seed")
    seed = int(args[i + 1])
    del args[i : i + 2]
if args and args[0] == "--":
    args = args[1:]
if seed is None:
    print("usage: generate_seeded.py --seed N -- <generate_dataset.py arguments>", file=sys.stderr)
    sys.exit(1)

script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "imitation_learning", "isaaclab_mimic", "generate_dataset.py")

from isaaclab.app import AppLauncher  # noqa: E402

_original_init = AppLauncher.__init__


def _patched_init(self, *a, **kw):
    _original_init(self, *a, **kw)
    # the simulator is up now, so the Isaac Lab modules can be imported and patched before the script imports them
    import isaaclab_mimic.datagen.generation as generation

    original_setup = generation.setup_env_config

    def setup_env_config(*sa, **skw):
        env_cfg, success_term = original_setup(*sa, **skw)
        env_cfg.datagen_config.seed = seed
        print(f"[generate_seeded] datagen_config.seed = {seed}", flush=True)
        return env_cfg, success_term

    generation.setup_env_config = setup_env_config

    # RmpFlowController.initialize() re-downloads the robot description files to one shared local path for every
    # robot; two processes doing that at the same time read half-written files and Lula fails. Serialize it.
    import fcntl

    import isaaclab.controllers.rmp_flow as rmp_flow

    original_initialize = rmp_flow.RmpFlowController.initialize

    def locked_initialize(self, *ia, **ikw):
        with open("/tmp/isaaclab_rmpflow_init.lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                return original_initialize(self, *ia, **ikw)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    rmp_flow.RmpFlowController.initialize = locked_initialize


AppLauncher.__init__ = _patched_init
sys.argv = [script] + args
sys.path.insert(0, os.path.dirname(script))
runpy.run_path(script, run_name="__main__")
