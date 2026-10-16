"""
Attention monitoring using facial landmarks.
For your testing, this gives a reasonable attention score per face
using dlib landmarks + simple heuristics.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import cv2
import dlib
import numpy as np
from scipy.spatial import distance as dist

from database import Database
from config import (
    HEAD_POSE_WEIGHT,
    GAZE_WEIGHT,
    POSTURE_WEIGHT,
    SHAPE_PREDICTOR_PATH,
    EXPRESSION_WEIGHT,
)


class AttentionMonitor:
    def __init__(self) -> None:
        self.db = Database()

        self.detector = dlib.get_frontal_face_detector()
        try:
            self.predictor = dlib.shape_predictor(SHAPE_PREDICTOR_PATH)
        except Exception as exc:  # pragma: no cover - runtime diagnostic
            print(f"[WARN] Could not load shape predictor: {exc}")
            self.predictor = None

        # Eye aspect ratio thresholds
        self.EYE_AR_THRESH = 0.25

        # 3D model points for head pose
        self.model_points = np.array(
            [
                (0.0, 0.0, 0.0),  # Nose tip
                (0.0, -330.0, -65.0),  # Chin
                (-225.0, 170.0, -135.0),  # Left eye left corner
                (225.0, 170.0, -135.0),  # Right eye right corner
                (-150.0, -150.0, -125.0),  # Left mouth corner
                (150.0, -150.0, -125.0),  # Right mouth corner
            ]
        )

        # Camera intrinsics (set per camera)
        self.camera_matrix = None

    # ---------- Setup ----------

    def set_camera_matrix(self, frame_width: int, frame_height: int) -> None:
        focal_length = frame_width
        center = (frame_width / 2.0, frame_height / 2.0)
        self.camera_matrix = np.array(
            [
                [focal_length, 0, center[0]],
                [0, focal_length, center[1]],
                [0, 0, 1],
            ],
            dtype="double",
        )

    # ---------- Core helpers ----------

    def _eye_aspect_ratio(self, eye: np.ndarray) -> float:
        A = dist.euclidean(eye[1], eye[5])
        B = dist.euclidean(eye[2], eye[4])
        C = dist.euclidean(eye[0], eye[3])
        return (A + B) / (2.0 * C) if C > 0 else 0.0

    def _head_pose_score(self, shape: np.ndarray) -> float:
        if self.camera_matrix is None:
            return 0.5

        image_points = np.array(
            [
                shape[30],  # Nose tip
                shape[8],  # Chin
                shape[36],  # Left eye left corner
                shape[45],  # Right eye right corner
                shape[48],  # Left mouth corner
                shape[54],  # Right mouth corner
            ],
            dtype="double",
        )

        dist_coeffs = np.zeros((4, 1))
        try:
            success, rotation_vector, translation_vector = cv2.solvePnP(
                self.model_points, image_points, self.camera_matrix, dist_coeffs
            )
            if not success:
                return 0.5
            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
            pose_matrix = cv2.hconcat((rotation_matrix, translation_vector))
            _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(pose_matrix)
            yaw = euler_angles[1][0]
            pitch = euler_angles[0][0]
            yaw_score = max(0.0, 1.0 - abs(yaw) / 45.0)
            pitch_score = max(0.0, 1.0 - abs(pitch) / 30.0)
            return float(min(1.0, max(0.0, (yaw_score + pitch_score) / 2.0)))
        except Exception:
            return 0.5

    def _expression_score(self, shape: np.ndarray) -> float:
        # Extremely simplified mouth-based proxy for “engaged”
        mouth_top = shape[62]
        mouth_bottom = shape[66]
        mouth_left = shape[48]
        mouth_right = shape[54]

        mouth_width = dist.euclidean(mouth_left, mouth_right)
        mouth_height = dist.euclidean(mouth_top, mouth_bottom)
        ratio = mouth_height / mouth_width if mouth_width > 0 else 0.0

        # Map ratio to 0–1; arbitrary range tuned for typical faces
        return float(min(1.0, max(0.0, 1.0 - ratio * 2.0)))

    # ---------- Public API ----------

    def analyze_attention(
        self,
        frame: Any,
        face_location: Tuple[int, int, int, int],
        student_id: int | None = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Compute an overall attention score [0,1] plus breakdown.
        """
        if self.predictor is None:
            # Fallback: cannot do landmarks, return neutral
            return 0.5, {"overall": 0.5, "method": "fallback"}

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        top, right, bottom, left = face_location
        rect = dlib.rectangle(left, top, right, bottom)
        shape = self.predictor(gray, rect)
        shape_np = np.array([[p.x, p.y] for p in shape.parts()])

        head_pose_score = self._head_pose_score(shape_np)

        # Eyes
        left_eye = shape_np[36:42]
        right_eye = shape_np[42:48]
        ear_left = self._eye_aspect_ratio(left_eye)
        ear_right = self._eye_aspect_ratio(right_eye)
        ear = (ear_left + ear_right) / 2.0
        eyes_open_score = min(1.0, ear / self.EYE_AR_THRESH) if self.EYE_AR_THRESH > 0 else 0.5

        expression_score = self._expression_score(shape_np)

        # Simple placeholder gaze score
        gaze_score = 0.5

        # Weighted overall score
        overall = (
            HEAD_POSE_WEIGHT * head_pose_score
            + GAZE_WEIGHT * gaze_score
            + EXPRESSION_WEIGHT * expression_score
            + POSTURE_WEIGHT * eyes_open_score
        )

        details: Dict[str, Any] = {
            "overall": float(overall),
            "head_pose": float(head_pose_score),
            "gaze": float(gaze_score),
            "expression": float(expression_score),
            "posture": float(eyes_open_score),
            "eye_aspect_ratio": float(ear),
        }

        if student_id is not None:
            self.db.log_attention(student_id, details)

        return float(overall), details

