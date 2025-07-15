#!/usr/bin/env python3
"""
Offline Face Recognition Attendance System
Main Flask Application with GhostFaceNet and Anti-Spoofing Technology
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from PIL import Image
import json
import base64
from io import BytesIO

# Import our custom modules
from models import db, Employee, AttendanceRecord, SystemLog
from face_recognition_service import FaceRecognitionService
from anti_spoofing_service import AntiSpoofingService
from camera_service import CameraService
from utils import create_directories, setup_logging

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///data/attendance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_UPLOAD_SIZE', 16 * 1024 * 1024))  # 16MB
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['FACE_TEMPLATES_FOLDER'] = 'face_templates'

# Initialize extensions
db.init_app(app)
CORS(app)

# Initialize services
face_recognition_service = FaceRecognitionService()
anti_spoofing_service = AntiSpoofingService()
camera_service = CameraService()

# Setup logging
logger = setup_logging()

# Create necessary directories
create_directories()

@app.before_first_request
def create_tables():
    """Create database tables on first request"""
    db.create_all()
    logger.info("Database tables created")

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        # Get recent attendance records
        recent_records = AttendanceRecord.query.order_by(
            AttendanceRecord.timestamp.desc()
        ).limit(10).all()
        
        # Get employee count
        employee_count = Employee.query.count()
        
        # Get today's attendance count
        today = datetime.now().date()
        today_attendance = AttendanceRecord.query.filter(
            AttendanceRecord.timestamp >= today
        ).count()
        
        return render_template('dashboard.html',
                             recent_records=recent_records,
                             employee_count=employee_count,
                             today_attendance=today_attendance)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return render_template('dashboard.html',
                             recent_records=[],
                             employee_count=0,
                             today_attendance=0)

@app.route('/employees')
def employees():
    """Employee management page"""
    try:
        employees = Employee.query.all()
        return render_template('employees.html', employees=employees)
    except Exception as e:
        logger.error(f"Error loading employees: {str(e)}")
        flash('Error loading employees', 'error')
        return render_template('employees.html', employees=[])

@app.route('/attendance')
def attendance():
    """Attendance marking page with camera interface"""
    return render_template('attendance.html')

@app.route('/reports')
def reports():
    """Attendance reports page"""
    try:
        # Get attendance data for reports
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        records = AttendanceRecord.query.filter(
            AttendanceRecord.timestamp.between(start_date, end_date)
        ).order_by(AttendanceRecord.timestamp.desc()).all()
        
        return render_template('reports.html', records=records)
    except Exception as e:
        logger.error(f"Error loading reports: {str(e)}")
        flash('Error loading reports', 'error')
        return render_template('reports.html', records=[])

@app.route('/api/enroll_employee', methods=['POST'])
def enroll_employee():
    """API endpoint to enroll a new employee"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['employee_id', 'name', 'department', 'image_data']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing field: {field}'}), 400
        
        # Check if employee already exists
        existing_employee = Employee.query.filter_by(employee_id=data['employee_id']).first()
        if existing_employee:
            return jsonify({'success': False, 'message': 'Employee ID already exists'}), 400
        
        # Process face image and extract template
        image_data = data['image_data']
        if image_data.startswith('data:image'):
            # Remove data URL prefix
            image_data = image_data.split(',')[1]
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        image_array = np.array(image)
        
        # Anti-spoofing check
        if anti_spoofing_service.is_real_face(image_array):
            # Extract face template
            face_template = face_recognition_service.extract_face_template(image_array)
            
            if face_template is not None:
                # Create new employee
                new_employee = Employee(
                    employee_id=data['employee_id'],
                    name=data['name'],
                    department=data['department'],
                    email=data.get('email', ''),
                    face_template=face_template.tolist(),
                    is_active=True
                )
                
                db.session.add(new_employee)
                db.session.commit()
                
                logger.info(f"Employee enrolled: {data['employee_id']} - {data['name']}")
                return jsonify({'success': True, 'message': 'Employee enrolled successfully'})
            else:
                return jsonify({'success': False, 'message': 'No face detected in image'}), 400
        else:
            return jsonify({'success': False, 'message': 'Liveness check failed - please use a live photo'}), 400
            
    except Exception as e:
        logger.error(f"Error enrolling employee: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/mark_attendance', methods=['POST'])
def mark_attendance():
    """API endpoint to mark attendance using face recognition"""
    try:
        data = request.get_json()
        
        if 'image_data' not in data:
            return jsonify({'success': False, 'message': 'No image data provided'}), 400
        
        # Process image
        image_data = data['image_data']
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        image_array = np.array(image)
        
        # Anti-spoofing check
        if not anti_spoofing_service.is_real_face(image_array):
            return jsonify({'success': False, 'message': 'Liveness check failed'}), 400
        
        # Face recognition
        recognized_employee = face_recognition_service.recognize_face(image_array)
        
        if recognized_employee:
            employee_id, confidence = recognized_employee
            
            # Check if already marked attendance today
            today = datetime.now().date()
            existing_record = AttendanceRecord.query.filter(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.timestamp >= today
            ).first()
            
            if existing_record:
                return jsonify({
                    'success': False, 
                    'message': 'Attendance already marked today',
                    'employee_id': employee_id,
                    'time': existing_record.timestamp.strftime('%H:%M:%S')
                })
            
            # Mark attendance
            attendance_record = AttendanceRecord(
                employee_id=employee_id,
                timestamp=datetime.now(),
                confidence_score=confidence,
                status='present'
            )
            
            db.session.add(attendance_record)
            db.session.commit()
            
            # Get employee details
            employee = Employee.query.filter_by(employee_id=employee_id).first()
            
            logger.info(f"Attendance marked: {employee_id} at {datetime.now()}")
            
            return jsonify({
                'success': True,
                'message': 'Attendance marked successfully',
                'employee': {
                    'id': employee.employee_id,
                    'name': employee.name,
                    'department': employee.department
                },
                'timestamp': attendance_record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'confidence': confidence
            })
        else:
            return jsonify({'success': False, 'message': 'Face not recognized'}), 404
            
    except Exception as e:
        logger.error(f"Error marking attendance: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/camera_feed')
def camera_feed():
    """API endpoint for camera feed"""
    try:
        return camera_service.get_camera_feed()
    except Exception as e:
        logger.error(f"Error getting camera feed: {str(e)}")
        return jsonify({'success': False, 'message': 'Camera not available'}), 500

@app.route('/api/capture_frame', methods=['POST'])
def capture_frame():
    """API endpoint to capture a frame from camera"""
    try:
        frame = camera_service.capture_frame()
        if frame is not None:
            # Convert frame to base64
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return jsonify({
                'success': True,
                'image_data': f'data:image/jpeg;base64,{frame_base64}'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to capture frame'}), 500
    except Exception as e:
        logger.error(f"Error capturing frame: {str(e)}")
        return jsonify({'success': False, 'message': 'Camera error'}), 500

@app.route('/api/system_stats')
def system_stats():
    """API endpoint for system statistics"""
    try:
        stats = {
            'total_employees': Employee.query.count(),
            'active_employees': Employee.query.filter_by(is_active=True).count(),
            'today_attendance': AttendanceRecord.query.filter(
                AttendanceRecord.timestamp >= datetime.now().date()
            ).count(),
            'system_status': 'online',
            'camera_status': camera_service.is_camera_available(),
            'face_recognition_model': os.environ.get('FACE_RECOGNITION_MODEL', 'GhostFaceNet'),
            'anti_spoofing_enabled': os.environ.get('ANTI_SPOOFING_ENABLED', 'true').lower() == 'true'
        }
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        return jsonify({'error': 'Failed to get system stats'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for Docker"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'camera': 'available' if camera_service.is_camera_available() else 'unavailable'
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return render_template('error.html', error='Internal server error'), 500

if __name__ == '__main__':
    # Create directories and setup database
    create_directories()
    
    with app.app_context():
        db.create_all()
        logger.info("Application started")
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.environ.get('FLASK_ENV') == 'development'
    ) 