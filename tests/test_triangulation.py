"""Triangulation + pose-fit tests.

Everything here is CPU-only and free of SMPL-X weights. The plan calls for
<5 cm reconstruction error on synthetic joints; we demand <1 cm since the
fixture is noiseless.
"""
from __future__ import annotations

import numpy as np
import pytest

from nfl_gsplat.calibration.cameras_io import constant_track
from nfl_gsplat.errors import PoseFusionError
from nfl_gsplat.pose.fuse_smplx import (
    SMPLXFitConfig,
    fit_single_frame,
    fuse_sequence,
    rigid_translation_forward,
)
from nfl_gsplat.pose.triangulate import (
    TriangulationConfig,
    triangulate_joints_two_view,
)
from nfl_gsplat.utils.geometry import project_points
from tests.fixtures.generate import (
    PLAYER_ROOTS,
    TEMPLATE_JOINTS_22,
    _endzone_camera,
    _sideline_camera,
)


# --- Triangulation ----------------------------------------------------------

def _observations_for_player(root_xyz: np.ndarray, num_frames: int = 5):
    """Project a T-pose player through both fixture cameras and pack into the
    triangulate.py observation dict."""
    intr_s, pose_s = _sideline_camera()
    intr_e, pose_e = _endzone_camera()
    cameras = {
        "sideline": constant_track(intr_s, pose_s, num_frames),
        "endzone":  constant_track(intr_e, pose_e, num_frames),
    }

    joints_world = root_xyz[None, None, :] + TEMPLATE_JOINTS_22[None, :, :]
    joints_world = np.broadcast_to(joints_world, (num_frames,) + TEMPLATE_JOINTS_22.shape)

    obs = {}
    for cam, track in cameras.items():
        intr, pose = track.at(0)
        K, R, t = intr.K(), pose.R, pose.t
        flat = joints_world.reshape(-1, 3)
        uv = project_points(flat, K, R, t).reshape(num_frames, -1, 2)
        conf = np.full(uv.shape[:2], 0.9, dtype=np.float64)
        obs[cam] = {"uv": uv, "conf": conf}
    return obs, cameras, joints_world


def test_triangulate_two_view_recovers_joints_under_one_cm():
    obs, cams, gt = _observations_for_player(PLAYER_ROOTS[0], num_frames=3)
    cfg = TriangulationConfig(reproj_px_max=1.0, conf_min=0.5)
    res = triangulate_joints_two_view(obs, cams, cfg)
    assert res.valid.all(), "every joint should be valid on noiseless input"
    err = np.linalg.norm(res.joints3d - gt, axis=-1)
    assert err.max() < 0.01, f"worst-joint reconstruction error {err.max():.4f} m"


def test_triangulate_rejects_low_confidence():
    obs, cams, _ = _observations_for_player(PLAYER_ROOTS[0], num_frames=2)
    obs["sideline"]["conf"][:, 5] = 0.1       # kill joint 5 on sideline
    cfg = TriangulationConfig(reproj_px_max=20.0, conf_min=0.3)
    res = triangulate_joints_two_view(obs, cams, cfg)
    assert not res.valid[:, 5].any(), "low-conf joint must be invalidated"
    # Other joints are unaffected.
    assert res.valid[:, 0].all() and res.valid[:, 21].all()


def test_triangulate_rejects_high_reprojection():
    obs, cams, _ = _observations_for_player(PLAYER_ROOTS[1], num_frames=1)
    obs["endzone"]["uv"][0, 3] += np.array([50.0, 50.0])   # 50 px shove on joint 3
    cfg = TriangulationConfig(reproj_px_max=5.0, conf_min=0.3)
    res = triangulate_joints_two_view(obs, cams, cfg)
    assert not res.valid[0, 3], "joint with huge reproj error must be rejected"


# --- SMPL-X fit (trivial forward) ------------------------------------------

def test_fit_single_frame_recovers_translation():
    cfg = SMPLXFitConfig(min_valid_joints=10, max_iter=50)
    fwd = rigid_translation_forward(TEMPLATE_JOINTS_22, cfg)
    true_transl = np.array([3.0, -2.0, 0.92])
    target = TEMPLATE_JOINTS_22 + true_transl[None, :]
    valid = np.ones(cfg.num_body_joints, dtype=bool)

    init = np.zeros(cfg.body_pose_dim + cfg.global_orient_dim + cfg.transl_dim)
    params, rms = fit_single_frame(target, valid, init, fwd, cfg)

    tr = params[cfg.body_pose_dim + cfg.global_orient_dim:]
    np.testing.assert_allclose(tr, true_transl, atol=1e-4)
    assert rms < 1e-4


def test_fit_single_frame_handles_missing_joints():
    cfg = SMPLXFitConfig(min_valid_joints=10, max_iter=50)
    fwd = rigid_translation_forward(TEMPLATE_JOINTS_22, cfg)
    true_transl = np.array([1.0, 1.0, 0.0])
    target = TEMPLATE_JOINTS_22 + true_transl[None, :]
    target[5:12] = np.nan       # simulate missing limb data
    valid = np.ones(cfg.num_body_joints, dtype=bool)
    valid[5:12] = False

    init = np.zeros(cfg.body_pose_dim + cfg.global_orient_dim + cfg.transl_dim)
    params, rms = fit_single_frame(target, valid, init, fwd, cfg)

    tr = params[cfg.body_pose_dim + cfg.global_orient_dim:]
    np.testing.assert_allclose(tr, true_transl, atol=1e-4)


def test_fuse_sequence_propagates_warm_start():
    cfg = SMPLXFitConfig(min_valid_joints=10, max_iter=30,
                        min_frame_validity_frac=1.0)
    fwd = rigid_translation_forward(TEMPLATE_JOINTS_22, cfg)
    T = 6
    transls = np.array([[0.1 * t, 0.05 * t, 0.92] for t in range(T)])
    target = TEMPLATE_JOINTS_22[None, :, :] + transls[:, None, :]
    valid = np.ones((T, cfg.num_body_joints), dtype=bool)
    init = np.zeros(cfg.body_pose_dim + cfg.global_orient_dim + cfg.transl_dim)

    res = fuse_sequence(target, valid, init, fwd, cfg)
    np.testing.assert_allclose(res.transl, transls, atol=1e-3)
    assert res.valid_frames.all()
    assert (res.residual_rms_m < 1e-3).all()


def test_fuse_sequence_raises_when_too_few_frames_fit():
    cfg = SMPLXFitConfig(min_valid_joints=10,
                        min_frame_validity_frac=0.9)
    fwd = rigid_translation_forward(TEMPLATE_JOINTS_22, cfg)
    T = 10
    target = np.tile(TEMPLATE_JOINTS_22[None, :, :], (T, 1, 1))
    valid = np.ones((T, cfg.num_body_joints), dtype=bool)
    valid[2:] = False                  # kill 80% of frames
    init = np.zeros(cfg.body_pose_dim + cfg.global_orient_dim + cfg.transl_dim)

    with pytest.raises(PoseFusionError):
        fuse_sequence(target, valid, init, fwd, cfg)
