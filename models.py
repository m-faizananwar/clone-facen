#!/usr/bin/env python3
"""
Database Models for Offline Face Recognition Attendance System
SQLAlchemy models for Employee, AttendanceRecord, and SystemLog
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON, Text, Float, Boolean, DateTime, Integer
import json

# Initialize SQLAlchemy
db = SQLAlchemy()

class Employee(db.Model):
    """Employee model for storing employee information and face templates"""
    
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    position = db.Column(db.String(50), nullable=True)
    
    # Face recognition data
    face_template = db.Column(JSON, nullable=False)  # Stores face embedding as JSON array
    face_template_version = db.Column(db.String(10), default='1.0')
    
    # Enrollment information
    enrolled_date = db.Column(DateTime, default=datetime.utcnow)
    enrolled_by = db.Column(db.String(50), nullable=True)
    
    # Status
    is_active = db.Column(Boolean, default=True, nullable=False)
    last_updated = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='employee_ref', lazy=True)
    
    def __init__(self, employee_id, name, department, face_template, **kwargs):
        self.employee_id = employee_id
        self.name = name
        self.department = department
        self.face_template = face_template
        
        # Set optional fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """Convert employee object to dictionary"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'name': self.name,
            'department': self.department,
            'email': self.email,
            'phone': self.phone,
            'position': self.position,
            'enrolled_date': self.enrolled_date.isoformat() if self.enrolled_date else None,
            'is_active': self.is_active,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    def get_face_template_array(self):
        """Get face template as numpy array"""
        import numpy as np
        if self.face_template:
            return np.array(self.face_template)
        return None
    
    def __repr__(self):
        return f'<Employee {self.employee_id}: {self.name}>'

class AttendanceRecord(db.Model):
    """Attendance record model for storing attendance logs"""
    
    __tablename__ = 'attendance_records'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), db.ForeignKey('employees.employee_id'), nullable=False, index=True)
    timestamp = db.Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Recognition details
    confidence_score = db.Column(Float, nullable=False)
    recognition_time_ms = db.Column(Integer, nullable=True)  # Time taken for recognition
    
    # Attendance status
    status = db.Column(db.String(20), default='present', nullable=False)  # present, absent, late
    attendance_type = db.Column(db.String(20), default='check_in')  # check_in, check_out
    
    # Location and device info
    device_id = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    
    # Anti-spoofing results
    liveness_score = db.Column(Float, nullable=True)
    anti_spoofing_passed = db.Column(Boolean, default=True)
    
    # Additional metadata
    image_quality_score = db.Column(Float, nullable=True)
    face_detection_bbox = db.Column(JSON, nullable=True)  # Bounding box coordinates
    notes = db.Column(Text, nullable=True)
    
    def __init__(self, employee_id, confidence_score, **kwargs):
        self.employee_id = employee_id
        self.confidence_score = confidence_score
        
        # Set optional fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """Convert attendance record to dictionary"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'confidence_score': self.confidence_score,
            'recognition_time_ms': self.recognition_time_ms,
            'status': self.status,
            'attendance_type': self.attendance_type,
            'device_id': self.device_id,
            'location': self.location,
            'liveness_score': self.liveness_score,
            'anti_spoofing_passed': self.anti_spoofing_passed,
            'image_quality_score': self.image_quality_score,
            'notes': self.notes
        }
    
    @property
    def employee_name(self):
        """Get employee name from relationship"""
        if self.employee_ref:
            return self.employee_ref.name
        return None
    
    @property
    def employee_department(self):
        """Get employee department from relationship"""
        if self.employee_ref:
            return self.employee_ref.department
        return None
    
    def __repr__(self):
        return f'<AttendanceRecord {self.employee_id} at {self.timestamp}>'

class SystemLog(db.Model):
    """System log model for storing system events and audit trail"""
    
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Log details
    level = db.Column(db.String(10), nullable=False, index=True)  # INFO, WARNING, ERROR, CRITICAL
    category = db.Column(db.String(50), nullable=False, index=True)  # SYSTEM, SECURITY, ATTENDANCE, etc.
    message = db.Column(Text, nullable=False)
    
    # Source information
    source_module = db.Column(db.String(50), nullable=True)
    source_function = db.Column(db.String(50), nullable=True)
    
    # User/session information
    user_id = db.Column(db.String(50), nullable=True)
    session_id = db.Column(db.String(100), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(Text, nullable=True)
    
    # Additional data
    metadata = db.Column(JSON, nullable=True)
    error_details = db.Column(Text, nullable=True)
    
    def __init__(self, level, category, message, **kwargs):
        self.level = level.upper()
        self.category = category.upper()
        self.message = message
        
        # Set optional fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """Convert system log to dictionary"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.level,
            'category': self.category,
            'message': self.message,
            'source_module': self.source_module,
            'source_function': self.source_function,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'ip_address': self.ip_address,
            'metadata': self.metadata,
            'error_details': self.error_details
        }
    
    @classmethod
    def log_event(cls, level, category, message, **kwargs):
        """Class method to create and save log entry"""
        log_entry = cls(level=level, category=category, message=message, **kwargs)
        db.session.add(log_entry)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Failed to save log entry: {e}")
    
    def __repr__(self):
        return f'<SystemLog {self.level} {self.category} at {self.timestamp}>'

class SystemConfiguration(db.Model):
    """System configuration model for storing application settings"""
    
    __tablename__ = 'system_configuration'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(Text, nullable=True)
    value_type = db.Column(db.String(20), default='string')  # string, integer, float, boolean, json
    description = db.Column(Text, nullable=True)
    category = db.Column(db.String(50), nullable=True, index=True)
    
    is_encrypted = db.Column(Boolean, default=False)
    is_readonly = db.Column(Boolean, default=False)
    
    created_date = db.Column(DateTime, default=datetime.utcnow)
    updated_date = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(50), nullable=True)
    
    def __init__(self, key, value, **kwargs):
        self.key = key
        self.value = str(value) if value is not None else None
        
        # Set optional fields
        for key_name, value_item in kwargs.items():
            if hasattr(self, key_name):
                setattr(self, key_name, value_item)
    
    def get_value(self):
        """Get typed value based on value_type"""
        if self.value is None:
            return None
        
        try:
            if self.value_type == 'integer':
                return int(self.value)
            elif self.value_type == 'float':
                return float(self.value)
            elif self.value_type == 'boolean':
                return self.value.lower() in ('true', '1', 'yes', 'on')
            elif self.value_type == 'json':
                return json.loads(self.value)
            else:
                return self.value
        except (ValueError, TypeError, json.JSONDecodeError):
            return self.value
    
    def set_value(self, value):
        """Set value with automatic type conversion"""
        if self.value_type == 'json':
            self.value = json.dumps(value)
        else:
            self.value = str(value) if value is not None else None
    
    def to_dict(self):
        """Convert configuration to dictionary"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.get_value(),
            'value_type': self.value_type,
            'description': self.description,
            'category': self.category,
            'is_encrypted': self.is_encrypted,
            'is_readonly': self.is_readonly,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'updated_by': self.updated_by
        }
    
    @classmethod
    def get_config(cls, key, default=None):
        """Get configuration value by key"""
        config = cls.query.filter_by(key=key).first()
        return config.get_value() if config else default
    
    @classmethod
    def set_config(cls, key, value, **kwargs):
        """Set configuration value by key"""
        config = cls.query.filter_by(key=key).first()
        if config:
            config.set_value(value)
            config.updated_date = datetime.utcnow()
            for k, v in kwargs.items():
                if hasattr(config, k):
                    setattr(config, k, v)
        else:
            config = cls(key=key, value=value, **kwargs)
            db.session.add(config)
        
        try:
            db.session.commit()
            return config
        except Exception as e:
            db.session.rollback()
            raise e
    
    def __repr__(self):
        return f'<SystemConfiguration {self.key}={self.value}>' 