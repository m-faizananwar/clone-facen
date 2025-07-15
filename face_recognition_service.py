#!/usr/bin/env python3
"""
Face Recognition Service using DeepFace Framework with GhostFaceNet
Implements face detection, template extraction, and recognition functionality
"""

import os
import cv2
import numpy as np
from typing import Optional, Tuple, List
import logging
from deepface import DeepFace
from models import Employee, db
import time

logger = logging.getLogger(__name__)

class FaceRecognitionService:
    """Service for face recognition using GhostFaceNet via DeepFace"""
    
    def __init__(self):
        """Initialize the face recognition service"""
        self.model_name = os.environ.get('FACE_RECOGNITION_MODEL', 'GhostFaceNet')
        self.detector_backend = 'opencv'  # Fast and reliable
        self.distance_metric = 'cosine'
        self.threshold = 0.4  # Threshold for face recognition (lower = more strict)
        
        # Face detection parameters
        self.min_face_size = 80  # Minimum face size in pixels
        self.max_face_size = 800  # Maximum face size in pixels
        
        logger.info(f"Face Recognition Service initialized with model: {self.model_name}")
        
        # Warm up the model
        self._warm_up_model()
    
    def _warm_up_model(self):
        """Warm up the face recognition model by running a dummy prediction"""
        try:
            # Create a dummy image for warming up
            dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)
            dummy_img.fill(128)  # Gray image
            
            # Add a simple face-like pattern
            cv2.rectangle(dummy_img, (50, 50), (174, 174), (255, 255, 255), -1)
            cv2.circle(dummy_img, (90, 100), 10, (0, 0, 0), -1)  # Left eye
            cv2.circle(dummy_img, (134, 100), 10, (0, 0, 0), -1)  # Right eye
            cv2.rectangle(dummy_img, (100, 130), (124, 140), (0, 0, 0), -1)  # Nose
            cv2.rectangle(dummy_img, (85, 150), (139, 160), (0, 0, 0), -1)  # Mouth
            
            # Try to extract features
            DeepFace.represent(
                img_path=dummy_img,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )
            logger.info("Face recognition model warmed up successfully")
            
        except Exception as e:
            logger.warning(f"Failed to warm up model: {str(e)}")
    
    def detect_faces(self, image: np.ndarray) -> List[dict]:
        """
        Detect faces in an image
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of face detection results with bounding boxes
        """
        try:
            # Use DeepFace for face detection
            faces = DeepFace.extract_faces(
                img_path=image,
                detector_backend=self.detector_backend,
                enforce_detection=False,
                align=True
            )
            
            detected_faces = []
            for i, face in enumerate(faces):
                if face is not None:
                    # Convert normalized face back to original coordinates
                    h, w = face.shape[:2]
                    if h >= self.min_face_size and w >= self.min_face_size:
                        detected_faces.append({
                            'face': face,
                            'confidence': 1.0,  # DeepFace doesn't provide confidence
                            'bbox': [0, 0, w, h]  # Simplified bbox
                        })
            
            return detected_faces
            
        except Exception as e:
            logger.error(f"Face detection error: {str(e)}")
            return []
    
    def extract_face_template(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract face template (embedding) from an image
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Face template as numpy array or None if no face detected
        """
        try:
            start_time = time.time()
            
            # Extract face representation using DeepFace
            embeddings = DeepFace.represent(
                img_path=image,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=True,
                align=True
            )
            
            processing_time = (time.time() - start_time) * 1000
            logger.debug(f"Face template extraction took {processing_time:.2f}ms")
            
            if embeddings and len(embeddings) > 0:
                # Get the first face embedding
                embedding = embeddings[0]['embedding']
                return np.array(embedding, dtype=np.float32)
            else:
                logger.warning("No face detected for template extraction")
                return None
                
        except Exception as e:
            logger.error(f"Face template extraction error: {str(e)}")
            return None
    
    def compare_faces(self, template1: np.ndarray, template2: np.ndarray) -> float:
        """
        Compare two face templates and return similarity score
        
        Args:
            template1: First face template
            template2: Second face template
            
        Returns:
            Similarity score (0-1, higher is more similar)
        """
        try:
            if self.distance_metric == 'cosine':
                # Cosine similarity
                dot_product = np.dot(template1, template2)
                norm1 = np.linalg.norm(template1)
                norm2 = np.linalg.norm(template2)
                
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                
                cosine_sim = dot_product / (norm1 * norm2)
                # Convert to distance and then to similarity (0-1)
                cosine_distance = 1 - cosine_sim
                similarity = 1 - cosine_distance
                
            elif self.distance_metric == 'euclidean':
                # Euclidean distance
                distance = np.linalg.norm(template1 - template2)
                # Normalize to 0-1 (assuming max distance of 2 for normalized vectors)
                similarity = max(0, 1 - (distance / 2))
                
            else:
                # Default to cosine
                similarity = np.dot(template1, template2) / (
                    np.linalg.norm(template1) * np.linalg.norm(template2)
                )
            
            return float(np.clip(similarity, 0, 1))
            
        except Exception as e:
            logger.error(f"Face comparison error: {str(e)}")
            return 0.0
    
    def recognize_face(self, image: np.ndarray) -> Optional[Tuple[str, float]]:
        """
        Recognize a face in an image against enrolled employees
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Tuple of (employee_id, confidence) or None if not recognized
        """
        try:
            start_time = time.time()
            
            # Extract face template from input image
            query_template = self.extract_face_template(image)
            if query_template is None:
                logger.warning("No face detected in query image")
                return None
            
            # Get all active employees with face templates
            employees = Employee.query.filter_by(is_active=True).all()
            if not employees:
                logger.warning("No enrolled employees found")
                return None
            
            best_match = None
            best_score = 0.0
            
            # Compare against all enrolled employees
            for employee in employees:
                try:
                    # Get employee's face template
                    employee_template = employee.get_face_template_array()
                    if employee_template is None:
                        continue
                    
                    # Compare templates
                    similarity = self.compare_faces(query_template, employee_template)
                    
                    logger.debug(f"Employee {employee.employee_id} similarity: {similarity:.4f}")
                    
                    # Check if this is the best match so far
                    if similarity > best_score and similarity >= self.threshold:
                        best_score = similarity
                        best_match = employee.employee_id
                        
                except Exception as e:
                    logger.error(f"Error comparing with employee {employee.employee_id}: {str(e)}")
                    continue
            
            processing_time = (time.time() - start_time) * 1000
            
            if best_match:
                logger.info(f"Face recognized: {best_match} (confidence: {best_score:.4f}, "
                           f"time: {processing_time:.2f}ms)")
                return best_match, best_score
            else:
                logger.info(f"Face not recognized (best score: {best_score:.4f}, "
                           f"threshold: {self.threshold}, time: {processing_time:.2f}ms)")
                return None
                
        except Exception as e:
            logger.error(f"Face recognition error: {str(e)}")
            return None
    
    def verify_face(self, image: np.ndarray, employee_id: str) -> Tuple[bool, float]:
        """
        Verify if a face in an image matches a specific employee
        
        Args:
            image: Input image as numpy array
            employee_id: Employee ID to verify against
            
        Returns:
            Tuple of (is_match, confidence_score)
        """
        try:
            # Extract face template from input image
            query_template = self.extract_face_template(image)
            if query_template is None:
                return False, 0.0
            
            # Get employee's face template
            employee = Employee.query.filter_by(employee_id=employee_id, is_active=True).first()
            if not employee:
                logger.warning(f"Employee {employee_id} not found or inactive")
                return False, 0.0
            
            employee_template = employee.get_face_template_array()
            if employee_template is None:
                logger.warning(f"No face template for employee {employee_id}")
                return False, 0.0
            
            # Compare templates
            similarity = self.compare_faces(query_template, employee_template)
            is_match = similarity >= self.threshold
            
            logger.debug(f"Face verification for {employee_id}: {similarity:.4f} "
                        f"(threshold: {self.threshold})")
            
            return is_match, similarity
            
        except Exception as e:
            logger.error(f"Face verification error: {str(e)}")
            return False, 0.0
    
    def get_face_quality_score(self, image: np.ndarray) -> float:
        """
        Assess the quality of a face image for recognition
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Quality score (0-1, higher is better)
        """
        try:
            # Basic quality metrics
            quality_score = 1.0
            
            # Check image size
            h, w = image.shape[:2]
            if h < 100 or w < 100:
                quality_score *= 0.5
            
            # Check if image is too dark or too bright
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            mean_brightness = np.mean(gray)
            
            if mean_brightness < 50:  # Too dark
                quality_score *= 0.7
            elif mean_brightness > 200:  # Too bright
                quality_score *= 0.8
            
            # Check for blur (using Laplacian variance)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if laplacian_var < 100:  # Blurry
                quality_score *= 0.6
            
            # Detect faces to ensure there's a clear face
            faces = self.detect_faces(image)
            if not faces:
                quality_score = 0.0
            elif len(faces) > 1:
                quality_score *= 0.8  # Multiple faces reduce quality
            
            return float(np.clip(quality_score, 0, 1))
            
        except Exception as e:
            logger.error(f"Face quality assessment error: {str(e)}")
            return 0.0
    
    def update_threshold(self, new_threshold: float):
        """Update the recognition threshold"""
        if 0.0 <= new_threshold <= 1.0:
            self.threshold = new_threshold
            logger.info(f"Recognition threshold updated to {new_threshold}")
        else:
            logger.warning(f"Invalid threshold value: {new_threshold}")
    
    def get_model_info(self) -> dict:
        """Get information about the current model"""
        return {
            'model_name': self.model_name,
            'detector_backend': self.detector_backend,
            'distance_metric': self.distance_metric,
            'threshold': self.threshold,
            'min_face_size': self.min_face_size,
            'max_face_size': self.max_face_size
        } 