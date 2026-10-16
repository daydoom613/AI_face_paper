"""
Face recognition module for the Smart Classroom system.
Uses the `face_recognition` library (dlib + CNN/HOG) and the Database
to store encodings. This is designed for real-time use with a webcam.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import cv2
import face_recognition
import numpy as np

from database import Database
from config import FACE_RECOGNITION_TOLERANCE


@dataclass
class RecognizedFace:
    name: str
    roll_number: Optional[str]
    student_id: Optional[int]
    location: Tuple[int, int, int, int]
    confidence: float
    type: str  # "student" or "unknown"


class FaceRecognizer:
    def __init__(self) -> None:
        """Initialize face recognizer with encodings from the database."""
        self.db = Database()
        self.known_face_encodings: List[np.ndarray] = []
        self.known_face_ids: List[int] = []
        self.known_face_names: List[str] = []
        self.known_face_rolls: List[str] = []
        self.tolerance: float = FACE_RECOGNITION_TOLERANCE

        self.total_recognitions: int = 0
        self.failed_recognitions: int = 0

        self.load_known_faces()

    # ---------- Encodings management ----------

    def load_known_faces(self) -> None:
        """Load all registered faces from the database."""
        students = self.db.get_all_face_encodings()
        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []
        self.known_face_rolls = []

        for s in students:
            self.known_face_encodings.append(s["face_encoding"])
            self.known_face_ids.append(int(s["id"]))
            self.known_face_names.append(s["name"])
            self.known_face_rolls.append(s["roll_number"])

        self.db.log_system_event(
            "INFO",
            "FaceRecognizer",
            f"Loaded {len(self.known_face_names)} registered faces",
        )

    # ---------- Registration ----------

    def register_new_face(
        self,
        name: str,
        roll_number: str,
        student_class: str,
        section: str,
        image_path: str,
    ) -> Tuple[bool, str]:
        """
        Register a new student face from an image file.
        You will use this with your own test image first.
        """
        # Load image
        image = face_recognition.load_image_file(image_path)

        # Detect faces
        face_locations = face_recognition.face_locations(image)
        if not face_locations:
            return False, "No face detected in the image."

        # Encode
        encodings = face_recognition.face_encodings(image, face_locations)
        if not encodings:
            return False, "Could not encode face."

        face_encoding = encodings[0]

        # Save to DB
        student_id = self.db.add_student(
            roll_number=roll_number,
            name=name,
            student_class=student_class,
            section=section,
            face_encoding=face_encoding,
            face_image_path=image_path,
        )

        # Reload cache
        self.load_known_faces()
        return True, f"Student {name} registered successfully with ID {student_id}"

    # ---------- Recognition ----------

    def recognize_faces(self, frame: Any) -> List[Dict[str, Any]]:
        """
        Detect and recognize all faces in a BGR frame.
        Returns list of dicts (easier to JSON-serialize for API).
        """
        # Resize for speed
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Detect faces
        locations = face_recognition.face_locations(rgb_small)
        if not locations:
            return []

        encodings = face_recognition.face_encodings(rgb_small, locations)
        results: List[Dict[str, Any]] = []

        for loc, enc in zip(locations, encodings):
            top, right, bottom, left = loc
            # Scale back up
            top *= 2
            right *= 2
            bottom *= 2
            left *= 2
            location_scaled = (top, right, bottom, left)

            if self.known_face_encodings:
                distances = face_recognition.face_distance(self.known_face_encodings, enc)
                best_idx = int(np.argmin(distances))
                confidence = float(1 - distances[best_idx])

                if confidence >= self.tolerance:
                    face_type = "student"
                    name = self.known_face_names[best_idx]
                    roll = self.known_face_rolls[best_idx]
                    student_id = self.known_face_ids[best_idx]
                    self.total_recognitions += 1
                else:
                    face_type = "unknown"
                    name = "Unknown"
                    roll = None
                    student_id = None
                    self.failed_recognitions += 1
            else:
                face_type = "unknown"
                name = "Unknown"
                roll = None
                student_id = None
                confidence = 0.0
                self.failed_recognitions += 1

            results.append(
                {
                    "name": name,
                    "roll_number": roll,
                    "student_id": student_id,
                    "location": location_scaled,
                    "confidence": confidence,
                    "type": face_type,
                }
            )

        return results

    def recognize_single_face(self, frame: Any) -> Tuple[Optional[str], Optional[str], float]:
        """Recognize a single face (door-style use; kept for completeness)."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        if not locations:
            return None, None, 0.0

        encodings = face_recognition.face_encodings(rgb, locations)
        if not encodings:
            return None, None, 0.0

        enc = encodings[0]

        if self.known_face_encodings:
            distances = face_recognition.face_distance(self.known_face_encodings, enc)
            best_idx = int(np.argmin(distances))
            confidence = float(1 - distances[best_idx])
            if confidence >= self.tolerance:
                return (
                    self.known_face_names[best_idx],
                    self.known_face_rolls[best_idx],
                    confidence,
                )
            return None, None, confidence

        return None, None, 0.0

    # ---------- Stats ----------

    def get_recognition_stats(self) -> Dict[str, Any]:
        total = self.total_recognitions + self.failed_recognitions
        accuracy = (self.total_recognitions / total * 100.0) if total > 0 else 0.0
        return {
            "total_recognitions": self.total_recognitions,
            "failed_recognitions": self.failed_recognitions,
            "accuracy": accuracy,
            "known_faces": len(self.known_face_names),
        }

