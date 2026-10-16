## SmartClassroom Edge AI (Laptop Webcam Version)

This is an end‑to‑end implementation of your MCA project *“Design and Implementation of a Privacy‑Preserving Edge AI Framework for Intelligent Education”*, adapted for testing with a **single laptop webcam** instead of ESP32‑CAM hardware.

### 1. Project Structure

- **backend_python**: Python Flask backend, face recognition, attention monitoring, webcam analyzer.
- **frontend_java**: Java Swing GUI (dashboard + student enrollment) that talks to the backend.
- **database**: SQLite schema.
- **tests**: Minimal smoke test for the backend API.

### 2. Backend Setup (Windows)

1. **Install Python 3.8+** and make sure `python` / `pip` are on PATH.
2. Open a terminal in the project root:

   ```bash
   cd backend_python
   pip install -r requirements.txt
   ```

3. **Install dlib dependencies (if needed)**  
   On Windows it’s often easiest to install a prebuilt wheel, e.g.:

   ```bash
   pip install dlib
   pip install face-recognition
   ```

   (If `pip install -r requirements.txt` fails on `dlib`, install `dlib` first, then rerun `pip install -r requirements.txt` without `dlib`.)

4. **Download the landmark model**  
   - Download `shape_predictor_68_face_landmarks.dat.bz2` from  
     `http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2`
   - Extract it and place `shape_predictor_68_face_landmarks.dat` into:

     ```text
     backend_python/models/
     ```

5. **Initialize the database**:

   ```bash
   cd backend_python
   python init_db.py
   ```

6. **Run the backend server**:

   ```bash
   cd backend_python
   python server.py
   ```

   The Flask server listens on `http://localhost:5000`.

7. **Start the webcam analyzer** (from another terminal or via the Java UI):  
   - From Java dashboard you will simply start the camera using `/api/camera/start/0`.  
   - Or manually using HTTP:

     ```bash
     curl -X POST http://localhost:5000/api/camera/start/0
     ```

### 3. Registering Yourself (Test Student)

1. Make sure the backend is running.
2. Start the **Java frontend** (see next section).
3. Go to **Student Enrollment** tab.
4. Enter:
   - Roll number (e.g. `R001`)
   - Name (your name)
   - Class (e.g. `MCA`)
   - Section (e.g. `A`)
5. Click **Choose image** and select a clear face photo of yourself (front‑facing).
6. Click **Register**.  
   If successful, you’ll see a confirmation dialog and your record will appear in the table.

### 4. Java Swing Frontend Setup

1. **Install JDK 11+** and **Apache Ant**. Make sure `javac`, `java`, and `ant` are on PATH.
2. Download **Gson** JAR (for JSON parsing), e.g. `gson-2.10.1.jar`, and place it in:

   ```text
   frontend_java/lib/gson.jar
   ```

3. In a terminal at project root:

   ```bash
   cd frontend_java
   ant jar
   ```

4. Run the GUI:

   ```bash
   cd frontend_java
   java -jar dist/SmartClassroom.jar
   ```

5. Ensure `config.properties` points to your backend:

   ```text
   server.url=http://localhost:5000
   ```

### 5. Live Testing Flow

1. **Start backend** (`python server.py`).
2. **Start webcam analyzer**: from the Java dashboard (or POST `/api/camera/start/0`).
3. Register yourself via **Student Enrollment**.
4. Open **Dashboard**:
   - You should see the **live webcam feed** with a rectangle around your face.
   - Your **name / roll number** and confidence should appear on the overlay.
   - Stats (students detected, avg attention, FPS) update every ~2 seconds.

### 6. Notes & Limitations

- ESP32‑CAM and door‑lock code from the original document are **not required** for your current laptop‑only testing; they can be added later if you bring hardware.
- Attention scores are heuristic and mainly for demonstration; they are computed using head pose, eye openness, and a simple mouth‑based expression proxy.
- All data is stored locally in a SQLite file at `database/classroom.db`.

