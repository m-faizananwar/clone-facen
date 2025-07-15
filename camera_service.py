#!/usr/bin/env python3
"""
Camera Service for Face Recognition Attendance System
Handles video capture, frame processing, and camera management
"""

import cv2
import numpy as np
from typing import Optional, Generator
import logging
import threading
import time
from flask import Response

logger = logging.getLogger(__name__)

class CameraService:
    """Service for camera operations and video streaming"""
    
    def __init__(self, camera_id: int = 0):
        """
        Initialize the camera service
        
        Args:
            camera_id: Camera device ID (default: 0)
        """
        self.camera_id = camera_id
        self.cap = None
        self.is_streaming = False
        self.frame_rate = 30  # Target FPS
        self.frame_width = 640
        self.frame_height = 480
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        logger.info(f"Camera Service initialized for camera {camera_id}")
        
        # Initialize camera
        self._initialize_camera()
    
    def _initialize_camera(self):
        """Initialize camera capture"""
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera {self.camera_id}")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.frame_rate)
            
            # Try to capture a test frame
            ret, frame = self.cap.read()
            if ret:
                logger.info(f"Camera {self.camera_id} initialized successfully "
                           f"({frame.shape[1]}x{frame.shape[0]})")
                return True
            else:
                logger.error(f"Failed to capture test frame from camera {self.camera_id}")
                return False
                
        except Exception as e:
            logger.error(f"Camera initialization error: {str(e)}")
            return False
    
    def is_camera_available(self) -> bool:
        """Check if camera is available and working"""
        try:
            if self.cap is None:
                return False
            
            if not self.cap.isOpened():
                # Try to reinitialize
                self._initialize_camera()
                return self.cap is not None and self.cap.isOpened()
            
            # Try to capture a frame
            ret, _ = self.cap.read()
            return ret
            
        except Exception as e:
            logger.error(f"Camera availability check error: {str(e)}")
            return False
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame from the camera
        
        Returns:
            Captured frame as numpy array or None if failed
        """
        try:
            if not self.is_camera_available():
                logger.warning("Camera not available for frame capture")
                return None
            
            ret, frame = self.cap.read()
            if ret and frame is not None:
                # Store current frame
                with self.frame_lock:
                    self.current_frame = frame.copy()
                
                logger.debug(f"Frame captured: {frame.shape}")
                return frame
            else:
                logger.warning("Failed to capture frame")
                return None
                
        except Exception as e:
            logger.error(f"Frame capture error: {str(e)}")
            return None
    
    def start_streaming(self):
        """Start continuous video streaming"""
        if self.is_streaming:
            logger.warning("Camera streaming already started")
            return
        
        self.is_streaming = True
        streaming_thread = threading.Thread(target=self._streaming_loop, daemon=True)
        streaming_thread.start()
        logger.info("Camera streaming started")
    
    def stop_streaming(self):
        """Stop video streaming"""
        self.is_streaming = False
        logger.info("Camera streaming stopped")
    
    def _streaming_loop(self):
        """Main streaming loop running in background thread"""
        frame_time = 1.0 / self.frame_rate
        
        while self.is_streaming:
            start_time = time.time()
            
            frame = self.capture_frame()
            if frame is not None:
                with self.frame_lock:
                    self.current_frame = frame
            
            # Maintain frame rate
            elapsed_time = time.time() - start_time
            if elapsed_time < frame_time:
                time.sleep(frame_time - elapsed_time)
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Get the most recent frame
        
        Returns:
            Most recent frame or None
        """
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def generate_frames(self) -> Generator[bytes, None, None]:
        """
        Generator for streaming frames in MJPEG format
        
        Yields:
            Frame data as bytes
        """
        while True:
            frame = self.get_current_frame()
            if frame is None:
                frame = self.capture_frame()
            
            if frame is not None:
                # Add timestamp overlay
                frame_with_overlay = self._add_overlay(frame)
                
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame_with_overlay, 
                                         [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            time.sleep(1.0 / self.frame_rate)
    
    def get_camera_feed(self) -> Response:
        """
        Get Flask Response for camera feed streaming
        
        Returns:
            Flask Response with video stream
        """
        return Response(
            self.generate_frames(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    
    def _add_overlay(self, frame: np.ndarray) -> np.ndarray:
        """
        Add overlay information to frame
        
        Args:
            frame: Input frame
            
        Returns:
            Frame with overlay
        """
        try:
            overlay_frame = frame.copy()
            
            # Add timestamp
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(overlay_frame, timestamp, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Add status indicator
            status_text = "READY"
            status_color = (0, 255, 0)  # Green
            
            if not self.is_camera_available():
                status_text = "CAMERA ERROR"
                status_color = (0, 0, 255)  # Red
            
            cv2.putText(overlay_frame, status_text, (10, frame.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
            
            # Add face detection region indicator
            center_x, center_y = frame.shape[1] // 2, frame.shape[0] // 2
            face_region_size = 200
            
            # Draw face detection region
            cv2.rectangle(overlay_frame,
                         (center_x - face_region_size // 2, center_y - face_region_size // 2),
                         (center_x + face_region_size // 2, center_y + face_region_size // 2),
                         (255, 255, 0), 2)
            
            cv2.putText(overlay_frame, "Position face here", 
                       (center_x - 80, center_y + face_region_size // 2 + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            
            return overlay_frame
            
        except Exception as e:
            logger.error(f"Overlay addition error: {str(e)}")
            return frame
    
    def adjust_camera_settings(self, brightness: Optional[float] = None,
                             contrast: Optional[float] = None,
                             saturation: Optional[float] = None):
        """
        Adjust camera settings
        
        Args:
            brightness: Brightness value (0.0 - 1.0)
            contrast: Contrast value (0.0 - 1.0)
            saturation: Saturation value (0.0 - 1.0)
        """
        try:
            if not self.is_camera_available():
                logger.warning("Camera not available for settings adjustment")
                return
            
            if brightness is not None:
                self.cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
                logger.debug(f"Camera brightness set to {brightness}")
            
            if contrast is not None:
                self.cap.set(cv2.CAP_PROP_CONTRAST, contrast)
                logger.debug(f"Camera contrast set to {contrast}")
            
            if saturation is not None:
                self.cap.set(cv2.CAP_PROP_SATURATION, saturation)
                logger.debug(f"Camera saturation set to {saturation}")
                
        except Exception as e:
            logger.error(f"Camera settings adjustment error: {str(e)}")
    
    def set_resolution(self, width: int, height: int):
        """
        Set camera resolution
        
        Args:
            width: Frame width
            height: Frame height
        """
        try:
            if not self.is_camera_available():
                logger.warning("Camera not available for resolution change")
                return
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            self.frame_width = width
            self.frame_height = height
            
            logger.info(f"Camera resolution set to {width}x{height}")
            
        except Exception as e:
            logger.error(f"Resolution setting error: {str(e)}")
    
    def get_camera_info(self) -> dict:
        """
        Get camera information and settings
        
        Returns:
            Dictionary with camera information
        """
        try:
            if not self.is_camera_available():
                return {
                    'available': False,
                    'error': 'Camera not available'
                }
            
            return {
                'available': True,
                'camera_id': self.camera_id,
                'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': int(self.cap.get(cv2.CAP_PROP_FPS)),
                'brightness': self.cap.get(cv2.CAP_PROP_BRIGHTNESS),
                'contrast': self.cap.get(cv2.CAP_PROP_CONTRAST),
                'saturation': self.cap.get(cv2.CAP_PROP_SATURATION),
                'is_streaming': self.is_streaming
            }
            
        except Exception as e:
            logger.error(f"Camera info retrieval error: {str(e)}")
            return {
                'available': False,
                'error': str(e)
            }
    
    def save_frame(self, filename: str, frame: Optional[np.ndarray] = None) -> bool:
        """
        Save a frame to file
        
        Args:
            filename: Output filename
            frame: Frame to save (uses current frame if None)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if frame is None:
                frame = self.get_current_frame()
            
            if frame is None:
                frame = self.capture_frame()
            
            if frame is not None:
                success = cv2.imwrite(filename, frame)
                if success:
                    logger.info(f"Frame saved to {filename}")
                    return True
                else:
                    logger.error(f"Failed to save frame to {filename}")
                    return False
            else:
                logger.error("No frame available to save")
                return False
                
        except Exception as e:
            logger.error(f"Frame saving error: {str(e)}")
            return False
    
    def release(self):
        """Release camera resources"""
        try:
            self.stop_streaming()
            
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            
            logger.info("Camera resources released")
            
        except Exception as e:
            logger.error(f"Camera release error: {str(e)}")
    
    def __del__(self):
        """Destructor to ensure camera resources are released"""
        self.release() 