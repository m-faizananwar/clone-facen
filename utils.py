#!/usr/bin/env python3
"""
Utility Functions for Face Recognition Attendance System
Common helper functions for directory management, logging, and system utilities
"""

import os
import logging
import logging.handlers
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import hashlib
import secrets
from pathlib import Path
import cv2
import numpy as np

def create_directories():
    """Create necessary directories for the application"""
    directories = [
        'data',
        'uploads',
        'face_templates',
        'logs',
        'static/css',
        'static/js',
        'static/images',
        'templates',
        'exports'
    ]
    
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"Directory created/verified: {directory}")
        except Exception as e:
            print(f"Error creating directory {directory}: {e}")

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Setup logging configuration for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging format
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Create logger
    logger = logging.getLogger('face_recognition_system')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = os.path.join('logs', 'application.log')
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5  # 10MB per file, keep 5 backups
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_log_file = os.path.join('logs', 'errors.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file, maxBytes=5*1024*1024, backupCount=3  # 5MB per file, keep 3 backups
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)
    logger.addHandler(error_handler)
    
    logger.info("Logging system initialized")
    return logger

def generate_secret_key() -> str:
    """Generate a secure secret key for Flask sessions"""
    return secrets.token_hex(32)

def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        password: Plain text password
        hashed: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    return hash_password(password) == hashed

def validate_image(image_data: bytes) -> bool:
    """
    Validate if the provided data is a valid image
    
    Args:
        image_data: Binary image data
        
    Returns:
        True if valid image, False otherwise
    """
    try:
        # Try to decode the image
        np_arr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        # Check if image was decoded successfully
        if img is not None and img.size > 0:
            return True
        return False
        
    except Exception:
        return False

def resize_image(image: np.ndarray, max_size: int = 1024) -> np.ndarray:
    """
    Resize image while maintaining aspect ratio
    
    Args:
        image: Input image as numpy array
        max_size: Maximum dimension size
        
    Returns:
        Resized image
    """
    try:
        h, w = image.shape[:2]
        
        # Calculate scaling factor
        if max(h, w) <= max_size:
            return image
        
        if h > w:
            new_h = max_size
            new_w = int(w * (max_size / h))
        else:
            new_w = max_size
            new_h = int(h * (max_size / w))
        
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized
        
    except Exception as e:
        logging.error(f"Image resize error: {str(e)}")
        return image

def save_json(data: Dict[str, Any], filepath: str) -> bool:
    """
    Save data to JSON file
    
    Args:
        data: Data to save
        filepath: Output file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        logging.error(f"JSON save error: {str(e)}")
        return False

def load_json(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Load data from JSON file
    
    Args:
        filepath: Input file path
        
    Returns:
        Loaded data or None if failed
    """
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        logging.error(f"JSON load error: {str(e)}")
        return None

def get_file_size(filepath: str) -> int:
    """
    Get file size in bytes
    
    Args:
        filepath: Path to file
        
    Returns:
        File size in bytes, 0 if file doesn't exist
    """
    try:
        return os.path.getsize(filepath) if os.path.exists(filepath) else 0
    except Exception:
        return 0

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def clean_old_files(directory: str, days_old: int = 30, pattern: str = "*") -> int:
    """
    Clean old files from a directory
    
    Args:
        directory: Directory to clean
        days_old: Files older than this many days will be deleted
        pattern: File pattern to match (default: all files)
        
    Returns:
        Number of files deleted
    """
    try:
        if not os.path.exists(directory):
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        deleted_count = 0
        
        from glob import glob
        files = glob(os.path.join(directory, pattern))
        
        for filepath in files:
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_time < cutoff_date:
                    os.remove(filepath)
                    deleted_count += 1
                    logging.info(f"Deleted old file: {filepath}")
            except Exception as e:
                logging.error(f"Error deleting file {filepath}: {str(e)}")
        
        return deleted_count
        
    except Exception as e:
        logging.error(f"Directory cleanup error: {str(e)}")
        return 0

def get_system_info() -> Dict[str, Any]:
    """
    Get system information
    
    Returns:
        Dictionary with system information
    """
    import platform
    import psutil
    
    try:
        system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_usage': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free
            }
        }
        
        # Add GPU information if available
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                system_info['gpu'] = [
                    {
                        'name': gpu.name,
                        'memory_total': gpu.memoryTotal,
                        'memory_free': gpu.memoryFree,
                        'memory_used': gpu.memoryUsed,
                        'temperature': gpu.temperature,
                        'load': gpu.load
                    }
                    for gpu in gpus
                ]
        except ImportError:
            system_info['gpu'] = 'GPU information not available'
        
        return system_info
        
    except Exception as e:
        logging.error(f"System info retrieval error: {str(e)}")
        return {'error': str(e)}

def validate_employee_id(employee_id: str) -> bool:
    """
    Validate employee ID format
    
    Args:
        employee_id: Employee ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Allow alphanumeric characters, hyphens, and underscores
    # Length between 3 and 20 characters
    import re
    pattern = r'^[a-zA-Z0-9_-]{3,20}$'
    return bool(re.match(pattern, employee_id))

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    return sanitized if sanitized else 'unnamed_file'

def calculate_face_similarity_threshold(confidence_scores: List[float]) -> float:
    """
    Calculate optimal face similarity threshold based on confidence scores
    
    Args:
        confidence_scores: List of confidence scores from successful recognitions
        
    Returns:
        Recommended threshold value
    """
    if not confidence_scores:
        return 0.4  # Default threshold
    
    import statistics
    
    try:
        # Calculate statistics
        mean_score = statistics.mean(confidence_scores)
        stdev_score = statistics.stdev(confidence_scores) if len(confidence_scores) > 1 else 0.1
        
        # Set threshold to mean minus one standard deviation
        # This should capture most true positives while reducing false positives
        threshold = max(0.1, mean_score - stdev_score)
        
        return min(threshold, 0.8)  # Cap at 0.8 to avoid being too strict
        
    except Exception as e:
        logging.error(f"Threshold calculation error: {str(e)}")
        return 0.4

def export_attendance_data(records: List[Dict], format_type: str = 'csv') -> Optional[str]:
    """
    Export attendance data to file
    
    Args:
        records: List of attendance records
        format_type: Export format ('csv', 'json', 'excel')
        
    Returns:
        Export file path or None if failed
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type.lower() == 'csv':
            import csv
            filename = f'exports/attendance_export_{timestamp}.csv'
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if records:
                    fieldnames = records[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(records)
            
            return filename
            
        elif format_type.lower() == 'json':
            filename = f'exports/attendance_export_{timestamp}.json'
            
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(records, jsonfile, indent=2, default=str)
            
            return filename
            
        elif format_type.lower() == 'excel':
            try:
                import pandas as pd
                filename = f'exports/attendance_export_{timestamp}.xlsx'
                
                df = pd.DataFrame(records)
                df.to_excel(filename, index=False)
                
                return filename
            except ImportError:
                logging.error("pandas not available for Excel export")
                return None
        
        return None
        
    except Exception as e:
        logging.error(f"Data export error: {str(e)}")
        return None

def backup_database(db_path: str, backup_dir: str = 'backups') -> bool:
    """
    Create a backup of the database
    
    Args:
        db_path: Path to database file
        backup_dir: Directory to store backups
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import shutil
        
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'attendance_db_backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy database file
        shutil.copy2(db_path, backup_path)
        
        logging.info(f"Database backup created: {backup_path}")
        return True
        
    except Exception as e:
        logging.error(f"Database backup error: {str(e)}")
        return False 