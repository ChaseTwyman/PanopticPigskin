# Setup

The code raises a `SetupError` naming the section below whenever something it needs is missing.

## §1 Environments

Two Python environments, because the SMPL-X stack and the detection stack want different NumPy majors, and the pose
caches (`poses_*.json` holding pickled NumPy arrays) are written under NumPy 1:

| env | python | used for | install |
|---|---|---|---|
| **main** (`PY_MAIN`) | 3.10+ (3.14 used) | calibration, detection, tracking, identity (EasyOCR), keypoints (YOLOv8x-pose), the fine-tune's training, the tests | `pip install -r requirements/main.txt` then `pip install -e .` |
| **smplx** (`PY_SMPLX`) | 3.12 | SMPLest-X, the SMPL-X fits, the timeline, the renders, the rulers, the exports | `pip install -r requirements/smplx.txt` then `pip install -e . --no-deps` |

Install the CUDA build of PyTorch for your driver first (cu128 was used, on one RTX 4080). `scripts/pipeline_play.sh`
runs each stage in the environment it needs: `export PY_MAIN=... PY_SMPLX=...` (paths to the two interpreters).
Only the smplx environment may write the pose caches.

## §2 SMPL-X body model (licence-gated)

Register at https://smpl-x.is.tue.mpg.de and https://smpl.is.tue.mpg.de, accept the licences (non-commercial
research), download the model zips, then:

```bash
python scripts/00b_install_body_models.py path/to/models_smplx_v1_1.zip path/to/SMPL_python_v.1.1.0.zip
```

It extracts, renames to the layout below and validates each file by loading it:

```
data/body_models/smplx/SMPLX_NEUTRAL.npz
data/body_models/smpl/SMPL_NEUTRAL.pkl
```

The SMPL-X licence forbids redistributing the model; nothing in this repository ships it. (The Film Room draws its
players from exported joints only, for the same reason.)

## §3 Footage and calibration

Each play is a folder holding its two All-22 broadcast clips:

```
data/all22/<game>/<play>/sideline.mp4
data/all22/<game>/<play>/endzone.mp4
```

No annotation is needed: the cameras are solved from the field's own paint (yard lines, hash marks, numerals) by
`scripts/08_reconstruct_all22.py`, refined every frame (`08e`), moved into the rule-book field frame (`08d`, which
checks the line of scrimmage against the play description: `--los-yards`, e.g. "BLT 24" -> 24), and the endzone
camera is put on its own paint (`08l`). The footage is not included and is not redistributable.

## §4 Model weights

```bash
bash scripts/01_download_models.sh
```

fetches `yolov8m.pt`, `yolov8x.pt` and `yolov8x-pose.pt` into the repo root and clones SMPLest-X into
`third_party/SMPLest-X` (§8). The SMPLest-X-H32 checkpoint is manual: download it from the SMPLest-X release and place

```
third_party/SMPLest-X/pretrained_models/smplest_x_h/smplest_x_h.pth.tar
third_party/SMPLest-X/pretrained_models/smplest_x_h/config_base.py
```

The per-play fine-tuned keypoint model is trained by the pipeline itself (`FINETUNE=1`: `09g` pseudo-labels,
`09h` training) into `<play>/pose_ft2/`.

## §5 EasyOCR

The jersey reader downloads its detector and English recogniser to `~/.EasyOCR/model/` on first use.

## §6 Running a play

```bash
export PY_MAIN=... PY_SMPLX=...
bash scripts/pipeline_play.sh data/all22/<game>/<play> <play>/sideline.mp4 <play>/endzone.mp4 <los-yards> --from-paint
```

Every stage leaves a `.done_<stage>` marker in the play folder and is skipped on the next run; re-run the same command
to resume. The header of `scripts/pipeline_play.sh` lists every stage, its script and its outputs, and every knob
(environment variables) with its default. For a game other than the demo's, set `RED` to the team in the coloured
kit (one of the game's two teams; `08c` stops with a `SetupError` otherwise) and `OFFENCE` to the team with the
ball (default `RED`); `SNAP`, `QB` and `DOWN` are the ball stage's hand-read inputs (§7).

## §7 Hand-read inputs

- The ball's events: the snap, the passer's id and the frame the carrier is down, read off the film (`SNAP`, `QB`,
  `DOWN` for the `ball` stage); the release, the catch and the receiver are read from the ball in the sideline film.
- `<play>/film_reads.json`: depths for men neither camera can place (`tools/film_read_depth.py`).
- Identity fixes where the tracker swapped men inside a pile (`tools/film/*`, `scripts/08z_fold_ids.py`,
  `scripts/08za_drop_rows.py`).

`plays/` holds these for the demo play.

## §8 SMPLest-X checkout

`nfl_gsplat.pose.smplestx_infer` imports SMPLest-X's own modules (`main.config`, `human_models`, `utils`) from
`third_party/SMPLest-X` at runtime. SMPLest-X also needs its human-model files under
`third_party/SMPLest-X/human_models/human_model_files/{smplx,smpl}` (copy the §2 files there).

## §9 Rosters

Identity names players from the weekly roster (nflverse):

```bash
python scripts/fetch_nflverse_rosters.py --season 2024
```

writes `data/rosters/2024/rosters.parquet` and `roster_weekly.parquet` (not redistributed here).
