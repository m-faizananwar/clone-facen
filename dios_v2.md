# Simplified Project Scope: Offline Face Recognition Attendance System

## Overview

This project delivers a streamlined, offline attendance system that uses face recognition combined with anti-spoofing (liveness detection). The solution focuses on essential features for robustness, ease of use, and quick deployment.

## 1. Core Workflow

**Main Steps:**
1. **Anti-Spoofing:** The system checks if the face detected is from a live person (not a photo or screen).
2. **Attendance Logging:** If the face is real, the system recognizes the employee and records the check-in time in a local database.
3. **Employee Management:** New employees can be added, including automatic retraining/registration.

## 2. Technical Architecture

### Anti-Spoofing

- Detects if the camera input is a live person using passive liveness models (e.g., Simple Face).
- Prevents spoof attempts with photos, videos, or masks.
- Seamlessly integrates by running on each detected face before allowing recognition or logging.

### Face Recognition & Attendance

- After liveness is confirmed, the system performs automated face recognition with a lightweight model (e.g., GhostFaceNet).
- Matches embeddings against a local employee database.
- Records the employee ID, time, and liveness status in a secure attendance log.

### Employee Addition & Automatic Enrollment

- The admin can add a new employee with one or more face photos.
- The system extracts embeddings and updates the local database automatically—no manual retraining required.
- Supports easy updates as the employee roster changes.

## 3. Implementation Details

### Minimal Hardware & Software

- **Device:** Raspberry Pi 4 (4GB or higher), mid-range PC, or similar ARM/x86 edge platform.
- **Camera:** 720p or higher (USB webcam, Pi Cam).
- **Storage:** 32GB+ SD card or SSD.
- **Operating System:** Linux or Windows.

### Recommended Technology Stack

| Function            | Stack                        |
|---------------------|------------------------------|
| Face Detection      | -                            |
| Anti-Spoofing       | MiniFASNet or DeepFace API   |
| Face Recognition    | GhostFaceNet (via DeepFace)  |
| Database            | SQLite3 (local file)         |
| Backend/Script      | Python 3.x                   |
| UI (optional)       | Simple CLI or Web Dashboard  |

## 4. Basic System Workflow

1. **Start System:** Camera feed runs; system awaits faces.
2. **Detect Face:** Extract face region from camera input.
3. **Liveness Check:** 
   - If *not real*: Discard input, prompt for retry.
   - If *real*: Proceed to next step.
4. **Recognition:**
   - Match face against database of registered employees.
   - If matched: Log employee and check-in time.
   - If not: Optionally prompt for enrollment.
5. **Employee Addition:**
   - Admin adds a new employee with face images via dashboard or CLI.
   - System processes/uploaded images, extracts features, auto-updates database.
6. **Database:**
   - Stores employee details, face embeddings, attendance events (employee, date/time, liveness status).

## 5. Key Features and Recommendations

- **Offline capable:** All recognition and recording works with no internet.
- **Privacy:** No videos/photos stored unless explicitly needed.
- **Scalability:** Supports dozens to hundreds of employees with low hardware requirements.
- **Simplicity:** No manual model retraining required for new employees; system updates embeddings automatically.
- **Security:** Anti-spoofing blocks fake attempts; records liveness check results in attendance log.

## 6. High-Level Table: System Responsibilities

| Step               | Automatic? | Admin Input Needed? | Notes                           |
|--------------------|:----------:|:-------------------:|---------------------------------|
| Anti-spoofing      | Yes        | No                  | Always runs before recognition  |
| Face recognition   | Yes        | No                  | Runs on passing liveness check  |
| Attendance logging | Yes        | No                  | Data saved to local database    |
| Employee add/update| Yes        | Yes                 | Via dashboard/CLI               |
| Model retraining   | Yes        | No                  | Automatic, seamless for admin   |

## 7. Deployment Guidelines

- Plug in camera and power up device.
- Launch the attendance script or dashboard.
- Register employees via interface (add name and photos).
- System is now live: faces are checked for liveness, recognized, and attendance is logged in real time.

**Ongoing Tasks:**
- Review attendance records in the database.
- Add or remove employees as needed; no manual system restarts required.

**Summary:**  
The project is focused, requiring only essential components (live face check, employee verification, logging, and simple admin interface). Lightweight models and offline-capable code ensure reliable, efficient operation even on low-cost hardware. Automated database updates and enrollment minimize administrative effort and support smooth scaling.