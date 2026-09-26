"""Contract test for the SMPLest-X model adapter (pose.smplestx_infer).

The real model runs on a GPU; here we monkeypatch the adapter's model seam and
assert the I/O glue maps raw outputs into our NPZ schema correctly. CPU-only;
intentionally does NOT exercise torch / the third_party repo.
"""
from __future__ import annotations

import numpy as np

from nfl_gsplat.pose import smplestx_infer
from nfl_gsplat.pose.smplestx_infer import NUM_SMPLX_JOINTS, SMPLestXConfig


# --- T1.2 SMPLest-X ---------------------------------------------------------

def _raw_smplestx_sample():
    return {
        "betas": np.zeros(10),
        "body_pose": np.zeros((21, 3)),
        "global_orient": np.zeros(3),
        "transl": np.array([1.0, 2.0, 3.0]),
        "joints3d_cam": np.zeros((NUM_SMPLX_JOINTS, 3)),
        "joints2d": np.zeros((NUM_SMPLX_JOINTS, 2)),
        "confidence": np.ones(NUM_SMPLX_JOINTS),
    }


def test_smplestx_assembles_schema(monkeypatch):
    monkeypatch.setattr(smplestx_infer, "check_prerequisites", lambda cfg: None)
    monkeypatch.setattr(smplestx_infer, "_load_smplestx_model", lambda cfg: object())
    monkeypatch.setattr(
        smplestx_infer, "_smplestx_forward",
        lambda model, crops, bboxes, cfg: [_raw_smplestx_sample() for _ in range(len(crops))],
    )
    crops = np.zeros((3, 64, 64, 3), dtype=np.uint8)
    bboxes = np.zeros((3, 4))
    out = smplestx_infer.infer_crops(crops, bboxes, SMPLestXConfig())
    assert out["betas"].shape == (3, 10)
    assert out["body_pose"].shape == (3, 21, 3)
    assert out["joints3d_cam"].shape == (3, NUM_SMPLX_JOINTS, 3)
    assert np.allclose(out["transl"][0], [1.0, 2.0, 3.0])
