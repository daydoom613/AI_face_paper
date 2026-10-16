"""
SQLite database operations for Smart Classroom system.
This is a slightly simplified version focused on what you need
for testing: students, attendance, attention logs, access logs,
settings, and basic backup.
"""

from __future__ import annotations

import json
import os
import pickle
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import DB_PATH, DB_BACKUP_PATH


class Database:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self.connect()
        self.create_tables()

    def connect(self) -> None:
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    # ---------- Schema ----------

    def create_tables(self) -> None:
        """Create all required tables if they do not exist."""
        assert self.cursor is not None

        # Students table
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_number TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                class TEXT NOT NULL,
                section TEXT,
                face_encoding BLOB NOT NULL,
                face_image_path TEXT,
                registered_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
            """
        )

        # Attendance table
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                status TEXT DEFAULT 'present',
                confidence REAL,
                camera_id INTEGER,
                FOREIGN KEY (student_id) REFERENCES students(id),
                UNIQUE(student_id, date)
            )
            """
        )

        # Attention logs table
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS attention_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                attention_score REAL NOT NULL,
                head_pose_score REAL,
                gaze_score REAL,
                expression_score REAL,
                posture_score REAL,
                activity_type TEXT,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
            """
        )

        # Access logs table (kept simple)
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                person_type TEXT,
                status TEXT NOT NULL,
                confidence REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                image_path TEXT
            )
            """
        )

        # System logs table
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT,
                module TEXT,
                message TEXT
            )
            """
        )

        # Settings table
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        self.conn.commit()

        # Insert default settings
        default_settings = [
            ("recognition_tolerance", "0.6"),
            ("attention_threshold", "0.6"),
            ("auto_attendance", "true"),
            ("school_name", "Smart Classroom"),
            ("academic_year", datetime.now().strftime("%Y-%Y")),
        ]
        for key, value in default_settings:
            self.cursor.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        self.conn.commit()

    # ---------- Student Management ----------

    def add_student(
        self,
        roll_number: str,
        name: str,
        student_class: str,
        section: str,
        face_encoding: Any,
        face_image_path: Optional[str] = None,
    ) -> int:
        """Add or update a student with face encoding."""
        assert self.cursor is not None
        encoding_blob = pickle.dumps(face_encoding)
        try:
            self.cursor.execute(
                """
                INSERT INTO students (roll_number, name, class, section, face_encoding, face_image_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (roll_number, name, student_class, section, encoding_blob, face_image_path),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            # Update existing student
            self.cursor.execute(
                """
                UPDATE students
                SET name = ?, class = ?, section = ?, face_encoding = ?, face_image_path = ?,
                    registered_on = CURRENT_TIMESTAMP
                WHERE roll_number = ?
                """,
                (name, student_class, section, encoding_blob, face_image_path, roll_number),
            )
            self.conn.commit()
            student = self.get_student_by_roll(roll_number)
            return int(student["id"]) if student else -1

    def get_all_students(self) -> List[Dict[str, Any]]:
        assert self.cursor is not None
        self.cursor.execute(
            """
            SELECT id, roll_number, name, class, section, registered_on, is_active
            FROM students
            WHERE is_active = 1
            ORDER BY roll_number
            """
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def get_student_by_id(self, student_id: int) -> Optional[Dict[str, Any]]:
        assert self.cursor is not None
        self.cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_student_by_roll(self, roll_number: str) -> Optional[Dict[str, Any]]:
        assert self.cursor is not None
        self.cursor.execute("SELECT * FROM students WHERE roll_number = ?", (roll_number,))
        row = self.cursor.fetchone()
        if not row:
            return None
        result = dict(row)
        if result.get("face_encoding"):
            result["face_encoding"] = pickle.loads(result["face_encoding"])
        return result

    def get_all_face_encodings(self) -> List[Dict[str, Any]]:
        """Return all active students and their encodings."""
        assert self.cursor is not None
        self.cursor.execute(
            "SELECT id, roll_number, name, face_encoding FROM students WHERE is_active = 1"
        )
        students: List[Dict[str, Any]] = []
        for row in self.cursor.fetchall():
            student = dict(row)
            student["face_encoding"] = pickle.loads(student["face_encoding"])
            students.append(student)
        return students

    def delete_student(self, student_id: int) -> None:
        """Soft delete a student."""
        assert self.cursor is not None
        self.cursor.execute("UPDATE students SET is_active = 0 WHERE id = ?", (student_id,))
        self.conn.commit()

    # ---------- Attendance ----------

    def mark_attendance(self, student_id: int, confidence: float, camera_id: int = 0) -> bool:
        """Mark today's attendance for a student."""
        assert self.cursor is not None
        today = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")
        try:
            self.cursor.execute(
                """
                INSERT INTO attendance (student_id, date, time, confidence, camera_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (student_id, today, current_time, confidence, camera_id),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            self.cursor.execute(
                """
                UPDATE attendance
                SET time = ?, confidence = ?, camera_id = ?
                WHERE student_id = ? AND date = ?
                """,
                (current_time, confidence, camera_id, student_id, today),
            )
            self.conn.commit()
            return True

    def get_todays_attendance(self) -> List[Dict[str, Any]]:
        """Return today's attendance records with student details."""
        assert self.cursor is not None
        today = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute(
            """
            SELECT a.*, s.roll_number, s.name, s.class, s.section
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.date = ?
            ORDER BY a.time
            """,
            (today,),
        )
        return [dict(row) for row in self.cursor.fetchall()]

    # ---------- Attention ----------

    def log_attention(self, student_id: int, attention_scores: Dict[str, Any]) -> None:
        """Log attention metrics for a student."""
        assert self.cursor is not None
        self.cursor.execute(
            """
            INSERT INTO attention_logs
            (student_id, attention_score, head_pose_score, gaze_score, expression_score, posture_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                float(attention_scores.get("overall", 0)),
                float(attention_scores.get("head_pose", 0)),
                float(attention_scores.get("gaze", 0)),
                float(attention_scores.get("expression", 0)),
                float(attention_scores.get("posture", 0)),
            ),
        )
        self.conn.commit()

    # ---------- Logs ----------

    def log_access(
        self,
        name: str,
        person_type: str,
        status: str,
        confidence: float = 0.0,
        image_path: Optional[str] = None,
    ) -> None:
        assert self.cursor is not None
        self.cursor.execute(
            """
            INSERT INTO access_logs (name, person_type, status, confidence, image_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, person_type, status, confidence, image_path),
        )
        self.conn.commit()

    def get_recent_access_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        assert self.cursor is not None
        self.cursor.execute(
            """
            SELECT * FROM access_logs
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def log_system_event(self, level: str, module: str, message: str) -> None:
        assert self.cursor is not None
        self.cursor.execute(
            """
            INSERT INTO system_logs (level, module, message)
            VALUES (?, ?, ?)
            """,
            (level, module, message),
        )
        self.conn.commit()

    # ---------- Settings ----------

    def get_setting(self, key: str) -> Optional[str]:
        assert self.cursor is not None
        self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = self.cursor.fetchone()
        return row["value"] if row else None

    def update_setting(self, key: str, value: str) -> None:
        assert self.cursor is not None
        self.cursor.execute(
            """
            UPDATE settings
            SET value = ?, updated_on = CURRENT_TIMESTAMP
            WHERE key = ?
            """,
            (value, key),
        )
        self.conn.commit()

    # ---------- Backup ----------

    def backup_database(self) -> str:
        """Create a timestamped copy of the database file."""
        from shutil import copy2

        os.makedirs(DB_BACKUP_PATH, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(DB_BACKUP_PATH, f"classroom_backup_{timestamp}.db")

        # Close current connection before copy
        self.close()
        copy2(self.db_path, backup_path)
        # Reconnect for continued use
        self.connect()
        return backup_path

