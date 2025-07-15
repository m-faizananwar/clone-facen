from flask import Flask, render_template, request, jsonify, Response
import cv2
import json
import os
from datetime import datetime
import base64
import numpy as np
from deepface import DeepFace
import io
from PIL import Image
import threading
import time

app = Flask(__name__)

# Configuration
DB_PATH = "face_db"  # Directory to store employee face images
ATTENDANCE_FILE = "attendance.json"
EMPLOYEES_FILE = "employees.json"

# Global variables
camera = None
is_processing = False

class AttendanceSystem:
    def __init__(self):
        self.ensure_directories()
        self.load_data()
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        if not os.path.exists(DB_PATH):
            os.makedirs(DB_PATH)
        if not os.path.exists("templates"):
            os.makedirs("templates")
    
    def load_data(self):
        """Load existing data or create empty structures"""
        # Load employees
        if os.path.exists(EMPLOYEES_FILE):
            with open(EMPLOYEES_FILE, 'r') as f:
                self.employees = json.load(f)
        else:
            self.employees = {}
            self.save_employees()
        
        # Load attendance
        if os.path.exists(ATTENDANCE_FILE):
            with open(ATTENDANCE_FILE, 'r') as f:
                self.attendance = json.load(f)
        else:
            self.attendance = []
            self.save_attendance()
    
    def save_employees(self):
        """Save employees data to JSON"""
        with open(EMPLOYEES_FILE, 'w') as f:
            json.dump(self.employees, f, indent=2)
    
    def save_attendance(self):
        """Save attendance data to JSON"""
        with open(ATTENDANCE_FILE, 'w') as f:
            json.dump(self.attendance, f, indent=2)
    
    def add_employee(self, name, image_data):
        """Add a new employee to the database with antispoofing verification"""
        try:
            # Decode base64 image first
            image_bytes = base64.b64decode(image_data.split(',')[1])
            image = Image.open(io.BytesIO(image_bytes))
            
            # Save temporary image for antispoofing check
            temp_path = "temp_employee.jpg"
            image.save(temp_path)
            
            # Step 1: Antispoofing verification
            try:
                spoofing_result = DeepFace.extract_faces(
                    img_path=temp_path,
                    detector_backend="opencv",
                    enforce_detection=False,
                    anti_spoofing=True
                )
                
                if len(spoofing_result) == 0:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    return False, "No face detected in the image"
                
                # Check if face is real
                real_face_detected = False
                for face_result in spoofing_result:
                    if hasattr(face_result, 'is_real') and face_result.is_real:
                        real_face_detected = True
                        break
                    elif isinstance(face_result, dict) and face_result.get('is_real', False):
                        real_face_detected = True
                        break
                
                if not real_face_detected:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    return False, "Spoofing detected! Please use a real photo, not a screen capture or printed photo"
                
            except Exception as spoof_error:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False, f"Error during antispoofing verification: {str(spoof_error)}"
            
            # Step 2: If antispoofing passed, proceed with adding employee
            # Create employee directory
            employee_dir = os.path.join(DB_PATH, name.replace(" ", "_"))
            if not os.path.exists(employee_dir):
                os.makedirs(employee_dir)
            
            # Save the image to final location
            image_path = os.path.join(employee_dir, f"{name.replace(' ', '_')}.jpg")
            image.save(image_path)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Add to employees database
            self.employees[name] = {
                "id": len(self.employees) + 1,
                "name": name,
                "image_path": image_path,
                "created_at": datetime.now().isoformat()
            }
            
            self.save_employees()
            return True, "Employee added successfully with antispoofing verification"
        
        except Exception as e:
            # Clean up temp file if it exists
            if os.path.exists("temp_employee.jpg"):
                os.remove("temp_employee.jpg")
            return False, f"Error adding employee: {str(e)}"
    
    def recognize_face(self, image_data):
        """Recognize face from camera image with antispoofing"""
        global is_processing
        
        if is_processing:
            return None, "Processing previous request", False
        
        is_processing = True
        
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data.split(',')[1])
            image = Image.open(io.BytesIO(image_bytes))
            
            # Save temporary image
            temp_path = "temp_frame.jpg"
            image.save(temp_path)
            
            # Step 1: Antispoofing check
            try:
                spoofing_result = DeepFace.extract_faces(
                    img_path=temp_path,
                    detector_backend="opencv",
                    enforce_detection=False,
                    anti_spoofing=True
                )
                
                if len(spoofing_result) == 0:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    return None, "No face detected", False
                
                # Check if any face passes antispoofing
                real_face_detected = False
                for face_result in spoofing_result:
                    if hasattr(face_result, 'is_real') and face_result.is_real:
                        real_face_detected = True
                        break
                    elif isinstance(face_result, dict) and face_result.get('is_real', False):
                        real_face_detected = True
                        break
                
                if not real_face_detected:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    return None, "Spoofing detected! Please use a real face, not a photo or video", False
                
            except Exception as spoof_error:
                # If antispoofing fails, we'll continue with a warning but still try recognition
                print(f"Antispoofing check failed: {spoof_error}")
                # We'll proceed but mark it as potentially unsafe
            
            # Step 2: Face recognition (only if antispoofing passed)
            if os.path.exists(DB_PATH) and os.listdir(DB_PATH):
                try:
                    dfs = DeepFace.find(
                        img_path=temp_path,
                        db_path=DB_PATH,
                        model_name="GhostFaceNet",
                        detector_backend="opencv",
                        enforce_detection=False,
                        silent=True
                    )
                    
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
                    if len(dfs) > 0 and len(dfs[0]) > 0:
                        # Found a match
                        identity_path = dfs[0].iloc[0]['identity']
                        distance = dfs[0].iloc[0]['distance']
                        
                        # Extract employee name from path
                        employee_name = None
                        for name, info in self.employees.items():
                            if info['image_path'] in identity_path:
                                employee_name = name
                                break
                        
                        if employee_name and distance < 0.65:  # Threshold for recognition
                            return employee_name, f"Recognized with confidence: {1-distance:.2f}", True
                    
                    return None, "Face not recognized", True
                
                except Exception as e:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    return None, f"Recognition error: {str(e)}", True
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return None, "No employees in database", True
        
        except Exception as e:
            return None, f"Processing error: {str(e)}", False
        
        finally:
            is_processing = False
    
    def mark_attendance(self, employee_name):
        """Mark attendance for an employee with multiple in/out events per day and a 2-minute cooldown between events for the same person"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            now_time = datetime.now().strftime("%H:%M:%S")
            now_iso = datetime.now().isoformat()
            now_dt = datetime.now()
            # Find today's record for this employee
            today_record = None
            for record in self.attendance:
                if record.get('employee') == employee_name and record.get('date') == today:
                    today_record = record
                    break
            if today_record is None:
                # No record for today, create new with first event as 'in'
                new_record = {
                    "employee": employee_name,
                    "date": today,
                    "events": [
                        {"type": "in", "time": now_time, "timestamp": now_iso}
                    ]
                }
                self.attendance.append(new_record)
                self.save_attendance()
                return True, f"Clocked IN for {employee_name} at {now_time}"
            else:
                # There is a record for today, check last event
                events = today_record.get('events', [])
                if not events:
                    next_type = 'in'
                else:
                    last_event = events[-1]
                    last_type = last_event['type']
                    last_ts = last_event.get('timestamp')
                    # Cooldown check
                    if last_ts:
                        try:
                            last_dt = datetime.fromisoformat(last_ts)
                            diff = (now_dt - last_dt).total_seconds()
                            if diff < 120:
                                wait_sec = int(120 - diff)
                                return False, f"Please wait {wait_sec} seconds before next attendance event. Cooldown is 2 minutes between IN/OUT for the same person."
                        except Exception:
                            pass
                    next_type = 'out' if last_type == 'in' else 'in'
                events.append({"type": next_type, "time": now_time, "timestamp": now_iso})
                today_record['events'] = events
                self.save_attendance()
                return True, f"Clocked {'IN' if next_type == 'in' else 'OUT'} for {employee_name} at {now_time}"
        except Exception as e:
            return False, f"Error marking attendance: {str(e)}"

# Initialize the system
attendance_system = AttendanceSystem()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/add_employee', methods=['POST'])
def add_employee():
    """Add a new employee"""
    try:
        data = request.json
        name = data.get('name')
        image_data = data.get('image')
        
        if not name or not image_data:
            return jsonify({"success": False, "message": "Name and image are required"})
        
        success, message = attendance_system.add_employee(name, image_data)
        return jsonify({"success": success, "message": message})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/recognize', methods=['POST'])
def recognize():
    """Recognize face from camera with antispoofing"""
    try:
        data = request.json
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({"success": False, "message": "Image data required"})
        
        employee_name, message, is_real = attendance_system.recognize_face(image_data)
        
        if not is_real:
            return jsonify({
                "success": False,
                "message": message,
                "spoofing_detected": True
            })
        
        if employee_name:
            return jsonify({
                "success": True, 
                "employee": employee_name,
                "message": message,
                "spoofing_detected": False
            })
        else:
            return jsonify({
                "success": False,
                "message": message,
                "spoofing_detected": False
            })
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    """Mark attendance for recognized employee"""
    try:
        data = request.json
        employee_name = data.get('employee')
        
        if not employee_name:
            return jsonify({"success": False, "message": "Employee name required"})
        
        success, message = attendance_system.mark_attendance(employee_name)
        return jsonify({"success": success, "message": message})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/get_employees')
def get_employees():
    """Get list of all employees"""
    return jsonify(attendance_system.employees)

@app.route('/get_attendance')
def get_attendance():
    """Get attendance records"""
    return jsonify(attendance_system.attendance)

@app.route('/detect', methods=['POST'])
def detect():
    """Detect faces and return bounding boxes and liveness (spoofing) status"""
    try:
        data = request.json
        image_data = data.get('image')
        if not image_data:
            return jsonify({"success": False, "message": "Image data required"})
        # Decode base64 image
        image_bytes = base64.b64decode(image_data.split(',')[1])
        image = Image.open(io.BytesIO(image_bytes))
        temp_path = "temp_detect.jpg"
        image.save(temp_path)
        try:
            faces = DeepFace.extract_faces(
                img_path=temp_path,
                detector_backend="opencv",
                enforce_detection=False,
                anti_spoofing=True
            )
            results = []
            for face in faces:
                # face can be dict or object
                if isinstance(face, dict):
                    area = face.get('facial_area') or face.get('facialArea')
                    is_real = face.get('is_real', None)
                else:
                    area = getattr(face, 'facial_area', None)
                    is_real = getattr(face, 'is_real', None)
                if area:
                    results.append({
                        "x": area.get('x', 0),
                        "y": area.get('y', 0),
                        "w": area.get('w', 0),
                        "h": area.get('h', 0),
                        "is_real": is_real
                    })
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({"success": True, "faces": results})
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({"success": False, "message": f"Detection error: {str(e)}"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 