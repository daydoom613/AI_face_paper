-- Smart Classroom Database Schema (simplified for testing)

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
);

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
);

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
);

CREATE TABLE IF NOT EXISTS access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    person_type TEXT,
    status TEXT NOT NULL,
    confidence REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    image_path TEXT
);

CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT,
    module TEXT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

