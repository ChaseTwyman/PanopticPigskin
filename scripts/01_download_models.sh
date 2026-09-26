#!/usr/bin/env bash
# Fetch the non-gated pretrained weights and the SMPLest-X checkout the pipeline uses.
#
#   yolov8m.pt        person detection for calibration and tracking (08, 08b)
#   yolov8x.pt        high-resolution re-detection of missed players (03e, 08q)
#   yolov8x-pose.pt   2-D keypoints (05m) and the base of the per-play fine-tune (09h)
#   third_party/SMPLest-X   the SMPLest-X code (05c imports it at runtime)
#
# The YOLO weights land in the repo root, where the scripts look for them (Ultralytics would also fetch them on first
# use). The gated files are manual -- see SETUP.md:
#   data/body_models/smplx/SMPLX_NEUTRAL.npz (+ smpl/)      SETUP.md §2 (scripts/00b_install_body_models.py)
#   third_party/SMPLest-X/pretrained_models/smplest_x_h/    SETUP.md §4 (smplest_x_h.pth.tar + config_base.py)
#
# Uses aria2c when available (parallel, resumable) and falls back to wget -c.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPOS_DIR="$REPO_ROOT/third_party"
mkdir -p "$REPOS_DIR"

_fetch() {
    local url="$1" out="$2"
    if [[ -f "$out" ]]; then
        echo "  skip (exists): $out"
        return 0
    fi
    echo "  -> $url"
    if command -v aria2c >/dev/null 2>&1; then
        aria2c -x 8 -s 8 --continue=true -d "$(dirname "$out")" -o "$(basename "$out")" "$url"
    else
        wget --continue -O "$out" "$url"
    fi
}

echo "=== YOLOv8 weights (Ultralytics, AGPL-3.0) ==="
for w in yolov8m.pt yolov8x.pt yolov8x-pose.pt; do
    _fetch "https://github.com/ultralytics/assets/releases/download/v8.2.0/$w" "$REPO_ROOT/$w"
done

echo
echo "=== SMPLest-X ==="
if [[ -d "$REPOS_DIR/SMPLest-X/.git" ]]; then
    git -C "$REPOS_DIR/SMPLest-X" fetch --tags
else
    git clone https://github.com/wqyin/SMPLest-X "$REPOS_DIR/SMPLest-X"
fi

echo
echo "done. Still manual (licence-gated):"
echo "  - data/body_models/smplx/* and smpl/*     SETUP.md §2 (python scripts/00b_install_body_models.py)"
echo "  - third_party/SMPLest-X/pretrained_models/smplest_x_h/smplest_x_h.pth.tar + config_base.py   SETUP.md §4"
