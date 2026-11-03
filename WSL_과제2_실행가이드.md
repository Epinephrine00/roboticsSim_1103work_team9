# 실습 과제 2 (Agibot Toy2Box 모방학습) — WSL Ubuntu 22.04 실행 가이드

`[참고 자료] 모방학습_PDF_v1.1.pdf`의 단계를 이 PC(WSL2, RTX 3070 Ti 8GB)에서 그대로 진행하기 위한 메모입니다.
모든 명령은 아래 두 줄을 먼저 실행한 터미널에서 입력합니다.

```bash
conda activate lerobot-arena
cd ~/IsaacLab_RS
```

## 0. 현재 상태와 WSL 제약

| PDF 단계 | 상태 |
|---|---|
| 1. robomimic 설치 | 완료 (robomimic 0.4.0, Isaac Sim 5.1.0, IsaacLab_RS 연결됨) |
| 2. 키보드 데모 수집 | `./isaaclab.sh -p` 대신 `~/isaac_wsl_tools/teleop.sh` 사용 (아래 설명) |
| 2-5. replay `--video` | `~/isaac_wsl_tools/video.sh` 사용 |
| 4. annotate / generate | PDF 명령 그대로 (annotate에는 `--headless` 추가) |
| 5. train / play | PDF 명령 그대로 (play 영상은 `video.sh`) |

WSL2용 NVIDIA 드라이버에는 Vulkan 레이트레이싱이 없어서 Isaac Sim 창(RTX 렌더러)이 뜨지 않습니다.
물리 연산(PhysX)은 WSL에서는 CPU로 돌아갑니다. GPU PhysX는 Kit의 GPU foundation(NVIDIA Vulkan 드라이버)이 있어야 만들어지는데 WSL에는 NVIDIA Vulkan ICD가 없고, `--/physics/cudaDevice=0`, `--/persistent/physics/useActiveCudaContext=true`, `--/persistent/physics/overrideGPUSettings=2` 설정으로도 물리 시간과 GPU 메모리가 전혀 바뀌지 않는 것을 확인했습니다(2026-11-02). 신경망 학습과 추론(torch)은 GPU로 정상 동작합니다. 다만 속도 병목은 물리가 아니라 RMPFlow가 env마다 CPU에서 순차 계산되는 구조라, GPU 물리가 되는 네이티브 리눅스에서도 단계별 시간은 크게 다르지 않습니다. 그래서 데모 수집은
**시뮬레이터를 headless로 돌리고, 별도 뷰어 창("Isaac WSL teleop")에 장면을 그려 주면서 그 창에서 키를 받는 방식**으로 합니다.
공식 스크립트(`record_demos.py` 등)는 수정하지 않았고, 저장되는 HDF5 형식도 같습니다.

주의: Windows 쪽 프로그램이 GPU 메모리를 많이 쓰고 있습니다(확인 시점 8GB 중 약 5.8GB: Wallpaper Engine, OBS, Chrome, 게임 런처 등).
시뮬레이터를 돌리기 전에 가능한 한 닫아 두세요. 특히 Mimic 증강(`--num_envs 100`)과 학습 때 메모리 부족이 날 수 있습니다.

## 1. 데모 수집 (PDF 2단계)

조종 요령·세션 운영·점검표는 8주차 강의자료를 정리한 [데이터수집_가이드.md](데이터수집_가이드.md)에 있습니다. 조교 시범 20개는 `datasets/ta_toy2box_agibot.hdf5`(파이프라인 시험용, 제출 불가).

### 실행

```bash
~/isaac_wsl_tools/teleop.sh scripts/tools/record_demos.py --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0 --dataset_file ./datasets/toy2box_part1.hdf5 --num_demos 20 --teleop_device keyboard
```

- "Isaac WSL teleop" 창이 Windows 화면에 바로 뜨고, 시뮬레이터가 올라오는 약 1분 뒤부터 장면이 그려집니다. **창을 한 번 클릭해서 포커스를 준 뒤** 키를 누릅니다. 한/영 상태와 무관하게 동작합니다.
- 화면: 왼쪽 메인 뷰(드래그 회전, 휠 줌, 더블클릭 초기화), 오른쪽 위 = 위에서 본 뷰(화면 위 = +X), 오른쪽 아래 = 옆에서 본 뷰(화면 오른쪽 = +X, 위 = +Z).
- 그리퍼 위치에 월드 축(X 빨강, Y 초록, Z 파랑)과 바닥까지 내려오는 검은 선이 표시됩니다. 아래 상태줄에 저장된 데모 수, 현재 step, 그리퍼 상태, 누르고 있는 키가 나옵니다.
- 연습용 `teleop_se3_agent.py`도 같은 방식으로 실행할 수 있지만, 그냥 `record_demos.py`를 연습용 파일 이름(예: `./datasets/practice.hdf5`)으로 실행하는 편이 간단합니다. 실패한 시도는 저장되지 않습니다.

| 기능 | 키 |
|---|---|
| +X / -X | W / S |
| +Y / -Y | A / D |
| +Z / -Z | Q / E |
| Roll ± | Z / X |
| Pitch ± | T / G |
| Yaw ± | C / V |
| 그리퍼 열기/닫기 토글 | K |
| 현재 시도 버리고 리셋 | R |

### 성공 판정과 저장 규칙 (코드 기준)

- 성공 조건: 장난감 트럭의 중심이 상자 중심에서 **수평 10 cm 이내**, 높이 차 10 cm 이내(상자 안에 놓이면 만족), 그리고 **그리퍼가 열린 상태**.
  이 조건이 **10 step 연속** 유지되면 자동으로 저장되고 환경이 리셋됩니다. 즉, 상자 안에 넣은 뒤 K로 그리퍼를 열고 잠깐 기다리면 됩니다.
- 성공한 에피소드만 파일에 기록됩니다(기록 즉시 디스크에 flush). 창을 닫거나 Ctrl+C로 끊어도 그때까지 저장된 데모는 남습니다.
- 트럭이 테이블 아래로 떨어지면 에피소드가 끝나고 리셋됩니다(저장 안 됨).
- `--num_demos` 개수를 채우면 자동 종료됩니다.
- `record_demos.py`는 `--dataset_file`을 **덮어쓰기 모드**로 엽니다. 그래서 `teleop.sh`는 이미 있는 파일을 지정하면 실행을 거부합니다.
  여러 번에 나눠 수집할 때는 `toy2box_part1.hdf5`, `toy2box_part2.hdf5`처럼 이름을 바꾸고, 나중에 합칩니다:

```bash
./isaaclab.sh -p merge_demos.py --inputs ./datasets/toy2box_part1.hdf5 ./datasets/toy2box_part2.hdf5 --output ./datasets/toy2box_agibot.hdf5
```

### 조작 팁

- 트럭은 매번 위치(x -0.15~0.20, y -0.30~-0.15)와 **yaw가 무작위**로 놓입니다. 상자는 x 0.25~0.35, y 0.0~0.10 쪽입니다.
- 순서: 위에서 본 뷰로 트럭 위에 그리퍼를 맞추기(W/S/A/D) → C/V로 손가락 방향을 트럭의 짧은 변에 맞추기 → E로 내리기 → K로 닫기 → Q로 들기 → 상자 위로 이동 → E로 내리기 → K로 열기 → 성공 저장 대기.
- 속도: 이 PC에서는 한 step(시뮬레이션 0.05 s)에 약 0.12 s가 걸려 **약 7 step/s**로 돕니다(실시간의 약 1/3, 물리 50 ms + RMPFlow 제어/관측 70 ms, 뷰어 전송 5 ms). PDF 기준 길이의 시범(500~800 step) 하나에 1~2분 정도 걸리는 셈입니다. 느린 만큼 조작은 여유 있고, 저장되는 데이터(step 단위)에는 영향이 없습니다. 더 늦추고 싶을 때만 `WSL_TELEOP_HZ=4 ~/isaac_wsl_tools/teleop.sh ...`처럼 씁니다(기본 30, 현재 속도보다 높으면 효과 없음).
- 과제 조건: 사람 시범 20~100개. 성공만 저장되므로 실패를 걱정할 필요는 없지만, 데이터 품질(멈춤 비율, 그리퍼 전환 횟수 등)은 연구 축 중 하나이므로 확인해 둘 가치가 있습니다.

### 수집 결과 확인

```bash
./isaaclab.sh -p summarize_demos.py --dataset_file ./datasets/toy2box_agibot.hdf5
```

```bash
~/isaac_wsl_tools/video.sh scripts/tools/replay_demos.py --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0 --dataset_file ./datasets/toy2box_agibot.hdf5 --num_envs 1 --video --video_folder ./videos/agibot_demos
```

replay 영상은 `./videos/agibot_demos/demo_N.mp4`로 생성됩니다(단순 형상 렌더).

## 2. Mimic 데이터 증강 (PDF 4단계)

```bash
./isaaclab.sh -p scripts/imitation_learning/isaaclab_mimic/annotate_demos.py --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-Rel-Mimic-v0 --auto --input_file ./datasets/toy2box_agibot.hdf5 --output_file ./datasets/toy2box_agibot_annotated.hdf5 --headless
```

```bash
./isaaclab.sh -p scripts/imitation_learning/isaaclab_mimic/generate_dataset.py --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-Rel-Mimic-v0 --headless --num_envs 100 --generation_num_trials 500 --input_file ./datasets/toy2box_agibot_annotated.hdf5 --output_file ./datasets/toy2box_agibot_mimic_v1_500.hdf5
```

- GPU 메모리 부족(CUDA out of memory)이 나면 `--num_envs`를 50, 20으로 줄입니다. 결과 개수는 `--generation_num_trials`가 정합니다.
- 병렬 생성: 한 프로세스는 CPU 한 코어만 쓰므로 [generate_parallel.sh](generate_parallel.sh)로 프로세스를 나누면 그만큼 빨라집니다(각 프로세스는 [generate_seeded.py](generate_seeded.py)로 다른 seed를 받고, 끝나면 공식 merge 도구로 합칩니다).
  `./generate_parallel.sh 4 25 500 ./datasets/toy2box_all_annotated.hdf5 ./datasets/toy2box_all_mimic_p4_500.hdf5`
- 소요 시간(이 PC 측정): RMPFlow가 env마다 CPU에서 차례로 계산되어 `--num_envs 100`이면 step당 약 1.0초(초당 env-step 약 99개), 16이면 약 74개로 env 수를 늘려도 거의 빨라지지 않습니다. 성공 500개가 모일 때까지 돌기 때문에 생성 성공률에 따라 1.5~3시간쯤 봅니다. 화면에 `N/M (x%) successful demos generated` 줄이 찍히니 10분쯤 지켜본 뒤 남은 시간을 가늠하세요. GPU 메모리는 거의 쓰지 않습니다.
- 과제 조건: Mimic 생성 시범은 최대 1,000개.

## 3. 학습 (PDF 5단계)

```bash
./isaaclab.sh -p scripts/imitation_learning/robomimic/train.py --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0 --algo bc --dataset ./datasets/toy2box_agibot_mimic_v1_500.hdf5 --name bc_rnn_seed101
```

- seed는 `source/isaaclab_tasks/isaaclab_tasks/manager_based/manipulation/place/config/agibot/agents/robomimic/bc_rnn_low_dim.json`의 `"seed"`(기본 101)로 바꿉니다. 111로 학습할 때는 값을 바꾼 뒤 `--name bc_rnn_seed111`로 실행합니다.
- `--name`을 꼭 다르게 주세요. 같은 실험 이름의 폴더가 이미 있으면 robomimic이 "overwrite? (y/n)"을 묻고, y를 누르면 **이전 체크포인트를 삭제**합니다.
- 결과: `./logs/robomimic/Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0/<실험 이름>/<학습 시작 시각>/models/model_epoch_N.pth` (100 epoch마다 저장, 기본 2000 epoch).
- 2000 epoch에 약 80분 걸립니다(이 PC에서 측정: epoch당 약 2.4초 = gradient step 100회, GPU 1.4초 + 데이터 로딩 0.7초). 학습은 headless라 WSL에서 제약이 없습니다. seed 101과 111은 `--name`만 다르게 해서 동시에 돌려도 됩니다(둘 합쳐 약 1.5~2시간).

## 4. 평가 (play)

```bash
~/isaac_wsl_tools/video.sh scripts/imitation_learning/robomimic/play.py --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0 --checkpoint ./logs/robomimic/Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0/bc_rnn_seed101/<학습 시작 시각>/models/model_epoch_2000.pth --num_rollouts 100 --horizon 800 --video --video_length 1000 --video_folder ./videos/agibot_bc_mimic --seed 42 --headless
```

- 영상이 필요 없으면 `./isaaclab.sh -p scripts/imitation_learning/robomimic/play.py ...`에서 `--video*` 옵션만 빼고 실행합니다. 성공률 출력은 같습니다.
- 소요 시간(이 PC 측정): play.py는 env 1개로 rollout을 순차 실행하고 time_out을 끄기 때문에 실패한 rollout은 800 step(40초)까지 갑니다. 100 rollout에 약 1.5~2시간입니다. 성공률 숫자는 `--video` 없이 재고, 발표용 영상은 따로 `--num_rollouts 3` 정도로 찍는 편이 빠릅니다. seed 101/111 두 평가는 동시에 돌려도 됩니다.
- 빠른 비교용: [eval_multienv.py](eval_multienv.py)는 같은 규칙(성공 판정, horizon 800, seed 42)으로 env 20개를 한 번에 돌려 100 rollout을 20~25분에 끝내고, rollout별 궤적을 npz로 남깁니다. 난수 소비 순서가 달라 공식 play.py와 숫자가 조금 다를 수 있으니 조건 비교에 쓰고, 보고하는 최종 수치는 play.py로 다시 잽니다.
  `./isaaclab.sh -p eval_multienv.py --checkpoint <model.pth> --num_envs 20 --num_rollouts 100 --horizon 800 --seed 42 --headless`
- 실패 유형 분류(과제의 진단 단계): [diagnose_failures.py](diagnose_failures.py)가 그 npz를 읽어 실패를 접근/파지/운반/배치로 나누고 rollout별 표를 출력합니다.
  `python diagnose_failures.py <model>_rollouts.npz --csv failures.csv`
- 과제 조건: 평가 seed 42, rollout 100회, horizon 800. 결과는 seed 101/111 모델의 성공률 평균 ± 표준편차로 보고.

## 5. 문제가 생기면

- **뷰어 창이 안 뜸**: WSLg가 꺼져 있는지 확인(`echo $DISPLAY`가 `:0`이어야 함). 창이 Windows 다른 창 뒤에 숨어 있을 수도 있습니다.
- **"teleop_viewer.py is not running" 또는 포트 사용 중**: 이전 실행이 남아 있는 경우. `pkill -f teleop_viewer.py; pkill -f wsl_teleop.py` 후 다시 실행.
- **키를 눌러도 반응 없음**: 뷰어 창을 클릭해서 포커스를 준 뒤 누르세요. 상태줄의 `keys:`에 누른 키가 표시되어야 합니다. WSLg에서는 Windows에서 활성화된 창만 키보드를 받으므로, 터미널 등 다른 창을 클릭하면 누르고 있던 키는 모두 해제됩니다. `WSL_TELEOP_DEBUG=1`을 붙여 실행하면 뷰어가 받은 키(`[viewer] press W`)와 시뮬레이터가 받은 키(`[sim] key W press`), step 속도가 터미널에 출력됩니다.
- **CUDA out of memory**: Windows GPU 프로그램을 닫고 다시 실행. 증강은 `--num_envs`를 줄입니다.
- **뷰어 화면을 파일로 남기고 싶을 때**: `WSL_TELEOP_SNAPSHOT_DIR=./videos/snap ~/isaac_wsl_tools/teleop.sh ...` (2초마다 PNG 저장).
- 시뮬레이터 로그에 `gpu.foundation` / `No device could be created` 오류가 여러 줄 나오는 것은 WSL에서 렌더러가 없어서 나오는 정상 메시지입니다.
