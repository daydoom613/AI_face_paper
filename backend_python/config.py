"""
Configuration settings for Smart Classroom Edge AI System
Adapted for testing with a single laptop webcam (camera_id=0).
"""

import os

# System Configuration
SYSTEM_NAME = "SmartClassroom Edge AI"
VERSION = "1.0.0"
DEBUG_MODE = True

# Server Configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5000
# Disable Flask debug reloader so the webcam analyzer thread is not
# killed and restarted while you are testing.
FLASK_DEBUG = False

# Database Configuration
DB_PATH = os.path.join("database", "classroom.db")
DB_BACKUP_PATH = os.path.join("database", "backups")

# Camera Configuration
# In your test setup we use only the laptop camera (id 0).
CLASSROOM_CAMERA_COUNT = 1
CAMERA_RESOLUTION = (640, 480)
CAPTURE_INTERVAL = 0.1  # seconds between processed frames in analyzer loop
FACE_DETECTION_CONFIDENCE = 0.6

# Face Recognition Settings
FACE_RECOGNITION_TOLERANCE = 0.6
MODEL_PATH = "models"
SHAPE_PREDICTOR_PATH = os.path.join(MODEL_PATH, "shape_predictor_68_face_landmarks.dat")

# Attention Monitoring Settings
ATTENTION_THRESHOLD = 0.6  # Below this = distracted
ENGAGEMENT_UPDATE_INTERVAL = 5  # seconds
HEAD_POSE_WEIGHT = 0.3
GAZE_WEIGHT = 0.3
EXPRESSION_WEIGHT = 0.2
POSTURE_WEIGHT = 0.2

# Alert Settings (kept for completeness, not required in laptop-only setup)
LOW_ATTENTION_ALERT_THRESHOLD = 0.4
INTRUDER_ALERT_ENABLED = False
TELEGRAM_BOT_ENABLED = False
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# ESP32 Configuration (not used in laptop-only testing but kept for compatibility)
ESP32_DOOR_LOCK_IP = "192.168.1.100"
ESP32_CAMERA_1_IP = "192.168.1.101"
ESP32_CAMERA_2_IP = "192.168.1.102"
DOOR_UNLOCK_DURATION = 3000  # milliseconds

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "classroom.log")
ACCESS_LOG_FILE = os.path.join(LOG_DIR, "access.log")
ATTENTION_LOG_FILE = os.path.join(LOG_DIR, "attention.log")

# API Endpoints (for frontend convenience)
API_BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
API_ENDPOINTS = {
    "recognize": "/api/recognize",
    "attendance": "/api/attendance",
    "attention": "/api/attention/current",
    "students": "/api/students",
    "logs": "/api/logs/system",
    "status": "/api/status",
    "unlock": "/api/unlock",
}

# Ensure required directories exist when module is imported
for directory in ["database", DB_BACKUP_PATH, LOG_DIR, MODEL_PATH]:
    os.makedirs(directory, exist_ok=True)

