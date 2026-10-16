"""
Flask server exposing the Smart Classroom backend APIs.
In your testing setup, this runs the webcam-based ClassroomAnalyzer
and provides endpoints consumed by the Java Swing frontend.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict

import cv2
import numpy as np
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

from classroom_analyzer import ClassroomAnalyzer
from config import (
    API_BASE_URL,
    CLASSROOM_CAMERA_COUNT,
    FLASK_DEBUG,
    SERVER_HOST,
    SERVER_PORT,
    SYSTEM_NAME,
    VERSION,
)
from database import Database
from face_recognition_module import FaceRecognizer

app = Flask(__name__)
CORS(app)

db = Database()
face_recognizer = FaceRecognizer()

# Single analyzer for laptop camera (id 0)
classroom_analyzers: Dict[int, ClassroomAnalyzer] = {
    0: ClassroomAnalyzer(camera_id=0),
}


# ---------- Utility ----------

def _ensure_analyzer(camera_id: int) -> ClassroomAnalyzer:
    if camera_id not in classroom_analyzers:
        classroom_analyzers[camera_id] = ClassroomAnalyzer(camera_id=camera_id)
    return classroom_analyzers[camera_id]


# ---------- Basic endpoints ----------

@app.get("/")
def home():
    return jsonify(
        {
            "name": SYSTEM_NAME,
            "version": VERSION,
            "status": "running",
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.get("/api/status")
def system_status():
    stats: Dict[str, Any] = {}
    for cam_id, analyzer in classroom_analyzers.items():
        if analyzer.is_running:
            stats[f"camera_{cam_id}"] = analyzer.get_classroom_stats()
    return jsonify(
        {
            "status": "online",
            "cameras": len([a for a in classroom_analyzers.values() if a.is_running]),
            "registered_students": len(face_recognizer.known_face_names),
            "recognition_stats": face_recognizer.get_recognition_stats(),
            "classroom_stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    )


# ---------- Students ----------

@app.get("/api/students")
def get_students():
    students = db.get_all_students()
    return jsonify({"total": len(students), "students": students})


@app.post("/api/students/register-from-image")
def register_student_from_image():
    """
    Simple helper for testing:
    - multipart/form-data with:
        name, roll_number, class, section, image (file)
    """
    if "image" not in request.files:
        return jsonify({"error": "image file required"}), 400

    image_file = request.files["image"]
    name = request.form.get("name", "Test Student")
    roll_number = request.form.get("roll_number", "R001")
    student_class = request.form.get("class", "MCA")
    section = request.form.get("section", "A")

    # Save image to disk (for traceability)
    uploads_dir = "uploads"
    import os

    os.makedirs(uploads_dir, exist_ok=True)
    save_path = os.path.join(uploads_dir, f"{roll_number}_{image_file.filename}")
    image_file.save(save_path)

    ok, msg = face_recognizer.register_new_face(
        name=name,
        roll_number=roll_number,
        student_class=student_class,
        section=section,
        image_path=save_path,
    )
    # Also refresh encodings in any running classroom analyzers so
    # live recognition immediately sees the new student.
    if ok:
        for analyzer in classroom_analyzers.values():
            analyzer.face_recognizer.load_known_faces()

    status = 200 if ok else 400
    return jsonify({"success": ok, "message": msg}), status


# ---------- Attendance ----------

@app.get("/api/attendance")
def get_attendance():
    records = db.get_todays_attendance()
    return jsonify(
        {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total": len(records),
            "records": records,
        }
    )


# ---------- Classroom / attention ----------

@app.get("/api/attention/current")
def attention_current():
    camera_id = request.args.get("camera_id", default=0, type=int)
    analyzer = _ensure_analyzer(camera_id)
    if not analyzer.is_running:
        return jsonify({"error": "Camera not running"}), 400

    stats = analyzer.get_classroom_stats()
    faces = analyzer.get_current_faces()
    students = [
        {
            "name": f["name"],
            "roll_number": f["roll_number"],
            "attention": f.get("attention_score", 0.0),
            "confidence": f.get("confidence", 0.0),
        }
        for f in faces
        if f["type"] == "student"
    ]
    return jsonify(
        {
            "camera_id": camera_id,
            "stats": stats,
            "students": students,
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.post("/api/camera/start/<int:camera_id>")
def camera_start(camera_id: int):
    analyzer = _ensure_analyzer(camera_id)
    if not analyzer.is_running:
        analyzer.start()
        db.log_system_event("INFO", "Camera", f"Camera {camera_id} started")
        return jsonify({"message": f"Camera {camera_id} started"})
    return jsonify({"message": f"Camera {camera_id} already running"})


@app.post("/api/camera/stop/<int:camera_id>")
def camera_stop(camera_id: int):
    analyzer = _ensure_analyzer(camera_id)
    if analyzer.is_running:
        analyzer.stop()
        db.log_system_event("INFO", "Camera", f"Camera {camera_id} stopped")
        return jsonify({"message": f"Camera {camera_id} stopped"})
    return jsonify({"message": f"Camera {camera_id} already stopped"})


@app.get("/api/camera/frame/<int:camera_id>")
def camera_frame(camera_id: int):
    analyzer = _ensure_analyzer(camera_id)
    if not analyzer.is_running:
        return jsonify({"error": "Camera not running"}), 400
    frame = analyzer.get_current_frame()
    if frame is None:
        return jsonify({"error": "No frame available"}), 404

    ok, buffer = cv2.imencode(".jpg", frame)
    if not ok:
        return jsonify({"error": "Encoding failed"}), 500

    return send_file(
        io.BytesIO(buffer.tobytes()),
        mimetype="image/jpeg",
        download_name="frame.jpg",
    )


# ---------- Logs & backup ----------

@app.get("/api/logs/system")
def system_logs():
    level = request.args.get("level", default="INFO")
    limit = request.args.get("limit", default=100, type=int)
    assert db.cursor is not None
    db.cursor.execute(
        """
        SELECT * FROM system_logs
        WHERE level = ? OR ? = 'ALL'
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (level, level, limit),
    )
    rows = [dict(r) for r in db.cursor.fetchall()]
    return jsonify({"level": level, "total": len(rows), "logs": rows})


@app.post("/api/backup")
def backup():
    path = db.backup_database()
    return jsonify({"message": "Backup created", "path": path})


if __name__ == "__main__":
    print(
        f"{SYSTEM_NAME} v{VERSION} – starting on {SERVER_HOST}:{SERVER_PORT} "
        f"(webcam-based classroom analyzer)"
    )
    # Do not auto-start camera; frontend will call /api/camera/start/0
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=FLASK_DEBUG)

