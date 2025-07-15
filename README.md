# Face Recognition Attendance System

A simple offline face recognition attendance system using DeepFace and GhostFaceNet for real-time employee recognition and attendance tracking.

## Features

- 🎥 Real-time camera feed for face detection
- 👤 Face recognition using GhostFaceNet model
- ✅ Automatic attendance marking with timestamp
- 📋 Employee management (add/remove employees)
- 💾 JSON-based data storage (employees and attendance)
- 🔒 Offline operation (no internet required)
- 🖥️ Simple web interface

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- Webcam/Camera access
- macOS, Linux, or Windows

### 2. Installation

1. Clone or download this project
2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   ```bash
   # On macOS/Linux:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Running the Application

1. Start the Flask server:
   ```bash
   python app.py
   ```

2. Open your web browser and go to:
   ```
   http://localhost:5001
   ```

## How to Use

### Adding New Employees

1. Click "Start Camera" to activate your webcam
2. Click "Capture for New Employee" to take a photo
3. Enter the employee's name in the text field
4. Click "Add Employee" to save them to the database

### Taking Attendance

1. Make sure the camera is started
2. Position the employee's face in front of the camera
3. Click "Recognize Face" 
4. If recognized, attendance will be automatically marked with timestamp

### Viewing Records

- **Registered Employees**: View all employees in the system
- **Today's Attendance**: See who has checked in today with timestamps

## File Structure

```
dios_project/
├── app.py                 # Main Flask application
├── templates/
│   └── index.html        # Web interface
├── requirements.txt      # Python dependencies
├── employees.json        # Employee database (auto-created)
├── attendance.json       # Attendance records (auto-created)
├── face_db/             # Employee face images (auto-created)
└── venv/                # Virtual environment
```

## Technical Details

### Technology Stack

- **Backend**: Flask (Python)
- **Face Recognition**: DeepFace with GhostFaceNet model
- **Face Detection**: OpenCV
- **Database**: JSON files for simplicity
- **Frontend**: HTML/CSS/JavaScript
- **Image Processing**: PIL/Pillow

### Recognition Process

1. Camera captures live video feed
2. User clicks "Recognize Face" to capture current frame
3. DeepFace extracts face embedding using GhostFaceNet
4. System compares embedding against stored employee faces
5. If match found (threshold < 0.65), employee is identified
6. Attendance is automatically marked with timestamp

### Data Storage

- `employees.json`: Stores employee information and metadata
- `attendance.json`: Stores all attendance records with timestamps
- `face_db/`: Directory containing employee face images organized by name

## Troubleshooting

### Port Already in Use
If port 5001 is busy, modify the port in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5002)  # Change to available port
```

### Camera Access Issues
- Ensure your browser has camera permissions
- Try refreshing the page if camera doesn't start
- Check if other applications are using the camera

### Face Recognition Not Working
- Ensure good lighting when adding employees
- Take multiple photos from different angles if needed
- Check that face is clearly visible and not too far from camera

### Performance Issues
- Close other applications using the camera
- Ensure sufficient system memory (4GB+ recommended)
- Use good quality camera (720p+)

## Security & Privacy

- All processing happens locally (offline)
- No face data is sent to external servers
- Employee images are stored locally in `face_db/` directory
- Delete employee folders to remove their data

## Future Enhancements

- [ ] Anti-spoofing/liveness detection
- [ ] Multiple face detection in single frame
- [ ] Export attendance reports (CSV/PDF)
- [ ] User authentication for admin access
- [ ] Database integration (SQLite/PostgreSQL)
- [ ] Email notifications for attendance
- [ ] Mobile-responsive interface

## Support

For issues or questions, check the troubleshooting section above or review the project requirements in `dios_v2.md`.

---

**Note**: This is a prototype implementation focused on core functionality. For production use, consider adding additional security measures, error handling, and database optimization. 