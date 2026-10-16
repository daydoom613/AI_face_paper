"""
Classroom-level analyzer that combines face recognition and attention monitoring
for a single camera (your laptop webcam in this setup).
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from config import ATTENTION_THRESHOLD, CAMERA_RESOLUTION, CAPTURE_INTERVAL
from database import Database
from face_recognition_module import FaceRecognizer
from attention_monitor import AttentionMonitor


class ClassroomAnalyzer:
    def __init__(self, camera_id: int = 0) -> None:
        self.camera_id = camera_id
        self.db = Database()
        self.face_recognizer = FaceRecognizer()
        self.attention_monitor = AttentionMonitor()

        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running: bool = False

        self.current_frame: Optional[Any] = None
        self.processed_frame: Optional[Any] = None
        self.detected_faces: List[Dict[str, Any]] = []

        self.frame_count: int = 0
        self.processing_times: List[float] = []

        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None

        # For simple automatic attendance
        self.marked_attendance_today: set[int] = set()

    # ---------- Lifecycle ----------

    def start(self) -> None:
        if self.is_running:
            return

        self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_RESOLUTION[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_RESOLUTION[1])
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        # Configure camera matrix for attention monitor
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.attention_monitor.set_camera_matrix(width, height)

        self.is_running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
            self.cap = None

    # ---------- Main loop ----------

    def _loop(self) -> None:
        while self.is_running and self.cap:
            start = time.time()
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.1)
                continue

            self.current_frame = frame.copy()

            processed, faces = self._analyze_frame(frame)

            with self.lock:
                self.processed_frame = processed
                self.detected_faces = faces

            dt = time.time() - start
            self.processing_times.append(dt)
            if len(self.processing_times) > 200:
                self.processing_times.pop(0)
            self.frame_count += 1

            sleep_time = max(0.0, CAPTURE_INTERVAL - dt)
            time.sleep(sleep_time)

    # ---------- Per-frame analysis ----------

    def _analyze_frame(self, frame: Any) -> tuple[Any, List[Dict[str, Any]]]:
        faces = self.face_recognizer.recognize_faces(frame)

        for face in faces:
            if face["type"] == "student":
                score, details = self.attention_monitor.analyze_attention(
                    frame, tuple(face["location"]), face["student_id"]
                )
                face["attention_score"] = score
                face["attention_details"] = details

                # Simple auto-attendance
                sid = face["student_id"]
                if sid is not None and sid not in self.marked_attendance_today:
                    self.db.mark_attendance(sid, face["confidence"], self.camera_id)
                    self.marked_attendance_today.add(sid)
            else:
                # Still run attention for unknowns (no DB logging)
                score, _ = self.attention_monitor.analyze_attention(
                    frame, tuple(face["location"])
                )
                face["attention_score"] = score

        annotated = self._draw_overlays(frame.copy(), faces)
        return annotated, faces

    def _draw_overlays(self, frame: Any, faces: List[Dict[str, Any]]) -> Any:
        for face in faces:
            top, right, bottom, left = face["location"]
            if face["type"] == "student":
                color = (0, 255, 0) if face.get("attention_score", 0) >= ATTENTION_THRESHOLD else (
                    0, 165, 255
                )
            else:
                color = (0, 0, 255)

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            label_base = f"{face['name']}"
            if face.get("roll_number"):
                label_base += f" ({face['roll_number']})"
            conf = face.get("confidence", 0.0)
            att = face.get("attention_score", 0.0)

            if face["type"] == "student":
                text = f"{label_base} - {conf:.2f} - A:{att:.2f}"
            else:
                text = f"Unknown - {conf:.2f}"

            (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (left, top - h - 6), (left + w, top), color, -1)
            cv2.putText(
                frame,
                text,
                (left, top - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        return frame

    # ---------- Public accessors ----------

    def get_current_frame(self) -> Optional[Any]:
        with self.lock:
            if self.processed_frame is None:
                return None
            return self.processed_frame.copy()

    def get_current_faces(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.detected_faces)

    def get_classroom_stats(self) -> Dict[str, Any]:
        faces = self.get_current_faces()
        students = [f for f in faces if f["type"] == "student"]
        unknowns = [f for f in faces if f["type"] == "unknown"]
        attention_scores = [f.get("attention_score", 0.0) for f in students]

        avg_attention = float(np.mean(attention_scores)) if attention_scores else 0.0

        avg_dt = float(np.mean(self.processing_times)) if self.processing_times else 0.0
        fps = 1.0 / avg_dt if avg_dt > 0 else 0.0

        return {
            "total_faces": len(faces),
            "students_detected": len(students),
            "unknown_detected": len(unknowns),
            "avg_attention": avg_attention,
            "attentive_students": sum(1 for s in attention_scores if s >= ATTENTION_THRESHOLD),
            "distracted_students": sum(1 for s in attention_scores if s < ATTENTION_THRESHOLD),
            "frame_count": self.frame_count,
            "avg_processing_time": avg_dt,
            "fps": fps,
        }

