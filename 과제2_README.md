# 실습 과제 2: Agibot Toy2Box 모방학습 성공률 향상 연구

과목 저장소(IsaacLab_RS)에 과제 수행 파일을 추가한 것입니다. 환경·성공 판정·종료 조건은 바꾸지 않았습니다.

## 제출물

| 항목 | 위치 |
|---|---|
| 최종 체크포인트 (학습 seed 101 / 111, epoch 2000) | `checkpoints/bc_rnn_seed101/model_epoch_2000.pth`, `checkpoints/bc_rnn_seed111/model_epoch_2000.pth` (baseline: 생성 시범 501개 전부로 학습) |
| 평가 명령 | `play_command.txt` (강의자료 44쪽 형식, seed 42 · 100회 · horizon 800) |
| 발표 자료 | `analysis/로보틱스시뮬레이션_과제2_9조.pptx` (12장, 최종본) |
| 분석 노트 | `분석_노트.md` |

## 연구 요약

- Baseline: 키보드 시범 20개 → 자동 주석 16개 → Isaac Lab Mimic 생성 501개 → BC-RNN(low-dim) 2000 epoch × 100 step, batch 100. 성공률(20 env 평가, seed 42, 100회) 28 % / 27 % (seed 101 / 111).
- 진단: 실패의 64 %가 파지·운반 단계이고, 이 실패들은 정책이 그리퍼를 닫았다 열었다 반복한다(그리퍼 명령 부호 전환 중앙값 8·6회, 성공은 2회). 생성 시범 501개 중 32 %가 재파지·못 듦·손가락 밀림이 있는 "지저분한 파지" 시범이다.
- 가설: 지저분한 파지 시범이 정책의 그리퍼 반복 전환을 만든다.
- 실험: 깨끗한 파지 162개 vs 지저분한 파지 162개 (개수·학습 조건·seed 동일). 판정 기준은 결과 전에 기록(두 seed 평균 10 %p 이상 차이 + 파지·운반 실패 비율 감소 + 전환 횟수 감소).
- 결과(20 env 평가, seed 42 · 100회 · horizon 800, 두 seed 평균 ± 표준편차): 깨끗한 파지 162개 **12.0 ± 1.0 %** vs 지저분한 파지 162개 **21.5 ± 1.5 %** (baseline 501개 27.5 ± 0.5 %, 공식 play.py로는 19 / 27 → 23.0 ± 4.0 %). 가설 기각.
- 해석: 깨끗한 시범만 배운 정책도 그리퍼를 똑같이 반복 전환한다. 반복 전환은 지저분한 시범의 모방이 아니라 첫 파지가 실패한 뒤(시범에 없는 상태) 나오는 증상이고, 지저분한 시범에 들어 있는 "첫 파지 실패 → 다시 열고 → 다시 닫아 듦" 구간이 회복 능력을 가르친다(첫 파지 실패 후 회복 26 % vs 16 %). 재파지·미끄러짐 구간은 걸러낼 나쁜 습관이 아니라 회복 데이터다.
- 후속 실험(개수 339로 확대, clean339 vs random339): 20 env 평가 21.0 ± 0.0 % vs 26.0 ± 1.0 %로 실험 1과 같은 방향(두 seed 모두 random이 높음)이라 결론을 유지한다. 다만 5 %p 차이는 단독으로는 유의하지 않고(p ≈ 0.24), 실험 1의 회복률 차이는 재현되지 않았다(24 % vs 24 %). 성공률은 선별보다 시범 개수에 좌우되었다(clean162 12.0 → clean339 21.0 → 501개 27.5 %). 자세한 수치·그림은 `분석_노트.md`, `analysis/results.json`, `analysis/fig_*.png` 참고.
- 실험 조건 4개의 공식 play.py 100회 평가는 CPU 예산 때문에 19회에서 중단했고(`logs/experiments/*.play_partial.log`), 조건 비교는 같은 규칙의 20 env 병렬 평가(`eval_multienv.py`)로 보고한다. 제출 모델(baseline)만 공식 100회 숫자가 있다.
- 용어 대응(발표 자료 ↔ 이 문서·노트): 첫 그립 후 상승 = 첫 닫기로 2초 안에 듦, 재파지 성공률 = 첫 파지 실패 후 회복(회복률), 재파지 후 성공 / 전체 성공 = 회복 거친 성공, 전환 횟수(그리퍼 여닫기) = 그리퍼 명령 부호 전환 횟수.

## 재현

```bash
# 데이터 (datasets/ 는 용량 때문에 저장소에 없음)
#   datasets/toy2box_all.hdf5            키보드 시범 20개
#   datasets/toy2box_all_annotated.hdf5  annotate_demos.py 결과 16개
#   datasets/toy2box_all_mimic_v1_500.hdf5  generate_dataset.py 결과 501개 (generate_parallel.sh: 3 프로세스 × 34 env)
python analysis/grasp_quality.py datasets/toy2box_all_mimic_v1_500.hdf5 --csv analysis/mimic500_grasp.csv   # clean/dirty 목록
python subset_hdf5.py --input datasets/toy2box_all_mimic_v1_500.hdf5 --output datasets/mimic_dirty162.hdf5 --list analysis/mimic500_grasp_dirty.txt
python subset_hdf5.py --input datasets/toy2box_all_mimic_v1_500.hdf5 --output datasets/mimic_clean162.hdf5 --list analysis/mimic500_grasp_clean.txt --random 162 --seed 0

# 학습 (공식 train.py와 같은 설정; JSON의 seed를 101 / 111로)
./isaaclab.sh -p scripts/imitation_learning/robomimic/train.py --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0 --algo bc --dataset datasets/mimic_clean162.hdf5
#   또는 Isaac Sim 없이 같은 학습 코드만 실행: python train_bc_nokit.py --dataset datasets/mimic_clean162.hdf5 --name bc_rnn_clean162_seed101 --seed 101
#   두 조건 × 두 seed를 한 번에: ./run_experiment.sh clean162=datasets/mimic_clean162.hdf5 dirty162=datasets/mimic_dirty162.hdf5

# 평가 (공식)
./isaaclab.sh -p scripts/imitation_learning/robomimic/play.py --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0 --checkpoint <체크포인트> --num_rollouts 100 --horizon 800 --seed 42 --headless
# 평가 (20 env 병렬, 실패 단계 분류용) — play.py와 같은 규칙이지만 초기 상태 추첨이 달라 성공률이 다를 수 있음
./run_evals.sh <체크포인트>        # eval_multienv.py + diagnose_failures.py
python analysis/plot_diagnosis.py  # 진단 그림
python analysis/collect_results.py      # 결과 표(analysis/results.json)·그림(fig_experiment.png, fig_followup.png)
python analysis/make_report_deck.py     # 발표 자료 analysis/로보틱스시뮬레이션_과제2_9조.pptx
```

## 추가한 파일

| 파일 | 내용 |
|---|---|
| `train_bc_nokit.py` | 공식 `train.py`의 학습 코드를 Isaac Sim 없이 실행 (WSL2에서 여러 학습을 동시에 돌리기 위해) |
| `run_experiment.sh`, `run_evals.sh`, `prepare_submission.sh` | 실험 일괄 실행, 평가+진단, 제출 파일 생성 |
| `eval_multienv.py`, `diagnose_failures.py` | 20 env 병렬 평가, 실패 단계(접근/파지/운반/배치) 분류 |
| `generate_seeded.py`, `generate_parallel.sh` | Mimic 생성을 seed를 달리해 3 프로세스로 병렬 실행 (WSL2 CPU 물리라서) |
| `subset_hdf5.py`, `merge_demos.py`, `summarize_demos.py` | 데이터셋 부분 집합·병합·요약 |
| `analysis/` | 파지 품질 분석, 그림, 결과 수집, 발표 자료 생성 스크립트 |
| `logs/experiments/` | 공식 play.py 평가 로그(baseline 100회 `*.play.log`, 실험 조건 19회 부분 로그 `*.play_partial.log`), 20 env 평가 로그(`fast_eval_*.log`), 실행 스크립트. 학습 로그(`*.train.log`, 약 40 MB)는 용량 때문에 제외 |
| `datasets/*.demos.txt` | 각 학습 조건에 들어간 시범 번호 목록(clean162·dirty162·clean339·random339). hdf5 파일 자체는 용량 때문에 제외 |
| `WSL_과제2_실행가이드.md`, `데이터수집_가이드.md` | WSL2에서 파이프라인을 돌리는 방법 (렌더러 없이 텔레오퍼레이션 포함) |
