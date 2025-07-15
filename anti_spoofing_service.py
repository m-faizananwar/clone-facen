#!/usr/bin/env python3
"""
Anti-Spoofing Service using MiniFASNet (Silent Face Anti-Spoofing)
Implements liveness detection to prevent photo, video, and mask attacks
"""

import os
import cv2
import numpy as np
from typing import Tuple, Optional
import logging
import time

logger = logging.getLogger(__name__)

class AntiSpoofingService:
    """Service for face anti-spoofing and liveness detection"""
    
    def __init__(self):
        """Initialize the anti-spoofing service"""
        self.enabled = os.environ.get('ANTI_SPOOFING_ENABLED', 'true').lower() == 'true'
        self.threshold = 0.5  # Threshold for liveness detection (higher = more strict)
        self.model_name = 'MiniFASNet'
        
        # Model parameters
        self.input_size = (80, 80)  # MiniFASNet input size
        self.model_loaded = False
        
        logger.info(f"Anti-Spoofing Service initialized (enabled: {self.enabled})")
        
        if self.enabled:
            self._load_model()
    
    def _load_model(self):
        """Load the MiniFASNet model for anti-spoofing"""
        try:
            # Try to import the silent face anti-spoofing library
            try:
                from silent_face_anti_spoofing import AntiSpoofPredict
                self.model = AntiSpoofPredict(device_id=0)
                self.model_loaded = True
                logger.info("MiniFASNet anti-spoofing model loaded successfully")
                
            except ImportError:
                logger.warning("silent-face-anti-spoofing library not found, using fallback method")
                self._init_fallback_detection()
                
        except Exception as e:
            logger.error(f"Failed to load anti-spoofing model: {str(e)}")
            self._init_fallback_detection()
    
    def _init_fallback_detection(self):
        """Initialize fallback anti-spoofing detection methods"""
        self.model_loaded = False
        logger.info("Using fallback anti-spoofing detection methods")
    
    def is_real_face(self, image: np.ndarray) -> bool:
        """
        Determine if the face in the image is real (not spoofed)
        
        Args:
            image: Input image as numpy array
            
        Returns:
            True if face is real, False if spoofed
        """
        if not self.enabled:
            return True  # Anti-spoofing disabled
        
        try:
            start_time = time.time()
            
            if self.model_loaded:
                # Use MiniFASNet model
                is_real, score = self._detect_with_minifasnet(image)
            else:
                # Use fallback methods
                is_real, score = self._detect_with_fallback(image)
            
            processing_time = (time.time() - start_time) * 1000
            
            logger.debug(f"Liveness detection: {'REAL' if is_real else 'SPOOFED'} "
                        f"(score: {score:.4f}, time: {processing_time:.2f}ms)")
            
            return is_real
            
        except Exception as e:
            logger.error(f"Anti-spoofing detection error: {str(e)}")
            # In case of error, default to allowing the face (fail open)
            return True
    
    def get_liveness_score(self, image: np.ndarray) -> float:
        """
        Get the liveness score for a face image
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Liveness score (0-1, higher means more likely to be real)
        """
        if not self.enabled:
            return 1.0
        
        try:
            if self.model_loaded:
                _, score = self._detect_with_minifasnet(image)
            else:
                _, score = self._detect_with_fallback(image)
            
            return score
            
        except Exception as e:
            logger.error(f"Liveness score calculation error: {str(e)}")
            return 1.0
    
    def _detect_with_minifasnet(self, image: np.ndarray) -> Tuple[bool, float]:
        """
        Detect spoofing using MiniFASNet model
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Tuple of (is_real, confidence_score)
        """
        try:
            # Preprocess image for MiniFASNet
            processed_image = self._preprocess_for_minifasnet(image)
            
            # Run inference
            prediction = self.model.predict(processed_image)
            
            # Extract results
            if isinstance(prediction, dict):
                score = prediction.get('score', 0.5)
                label = prediction.get('label', 0)
                is_real = label == 1  # 1 for real, 0 for spoof
            else:
                # Fallback for different return formats
                score = float(prediction) if isinstance(prediction, (int, float)) else 0.5
                is_real = score > self.threshold
            
            return is_real, score
            
        except Exception as e:
            logger.error(f"MiniFASNet detection error: {str(e)}")
            return True, 1.0  # Fail open
    
    def _detect_with_fallback(self, image: np.ndarray) -> Tuple[bool, float]:
        """
        Detect spoofing using fallback methods (heuristic-based)
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Tuple of (is_real, confidence_score)
        """
        try:
            # Multiple fallback checks
            scores = []
            
            # 1. Color distribution analysis
            color_score = self._analyze_color_distribution(image)
            scores.append(color_score)
            
            # 2. Texture analysis
            texture_score = self._analyze_texture(image)
            scores.append(texture_score)
            
            # 3. Frequency domain analysis
            frequency_score = self._analyze_frequency_domain(image)
            scores.append(frequency_score)
            
            # 4. Reflection analysis
            reflection_score = self._analyze_reflections(image)
            scores.append(reflection_score)
            
            # Combine scores
            final_score = np.mean(scores)
            is_real = final_score > self.threshold
            
            logger.debug(f"Fallback anti-spoofing scores: color={color_score:.3f}, "
                        f"texture={texture_score:.3f}, frequency={frequency_score:.3f}, "
                        f"reflection={reflection_score:.3f}, final={final_score:.3f}")
            
            return is_real, final_score
            
        except Exception as e:
            logger.error(f"Fallback detection error: {str(e)}")
            return True, 1.0
    
    def _preprocess_for_minifasnet(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for MiniFASNet model
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Preprocessed image
        """
        try:
            # Convert to RGB if needed
            if len(image.shape) == 3 and image.shape[2] == 3:
                # Assume BGR, convert to RGB
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image
            
            # Resize to model input size
            resized = cv2.resize(image_rgb, self.input_size)
            
            # Normalize
            normalized = resized.astype(np.float32) / 255.0
            
            return normalized
            
        except Exception as e:
            logger.error(f"Image preprocessing error: {str(e)}")
            return image
    
    def _analyze_color_distribution(self, image: np.ndarray) -> float:
        """
        Analyze color distribution to detect printed photos
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Score indicating likelihood of being real (0-1)
        """
        try:
            # Convert to HSV for better color analysis
            if len(image.shape) == 3:
                hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            else:
                return 0.5  # Cannot analyze color on grayscale
            
            # Analyze saturation distribution
            saturation = hsv[:, :, 1]
            sat_mean = np.mean(saturation)
            sat_std = np.std(saturation)
            
            # Real faces typically have higher saturation variance
            if sat_std > 20 and sat_mean > 50:
                color_score = 0.8
            elif sat_std > 10 and sat_mean > 30:
                color_score = 0.6
            else:
                color_score = 0.3
            
            # Analyze color histogram
            hist_b = cv2.calcHist([image], [0], None, [256], [0, 256])
            hist_g = cv2.calcHist([image], [1], None, [256], [0, 256])
            hist_r = cv2.calcHist([image], [2], None, [256], [0, 256])
            
            # Calculate histogram entropy (real faces have more diverse colors)
            def entropy(hist):
                hist = hist.flatten()
                hist = hist[hist > 0]
                return -np.sum(hist * np.log2(hist + 1e-10))
            
            avg_entropy = (entropy(hist_b) + entropy(hist_g) + entropy(hist_r)) / 3
            
            # Combine scores
            if avg_entropy > 6:
                entropy_score = 0.8
            elif avg_entropy > 4:
                entropy_score = 0.6
            else:
                entropy_score = 0.3
            
            return (color_score + entropy_score) / 2
            
        except Exception as e:
            logger.error(f"Color distribution analysis error: {str(e)}")
            return 0.5
    
    def _analyze_texture(self, image: np.ndarray) -> float:
        """
        Analyze texture patterns to detect printed photos or screens
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Score indicating likelihood of being real (0-1)
        """
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Calculate Local Binary Pattern (LBP) variance
            # Real faces have more texture variation
            lbp = self._calculate_lbp(gray)
            lbp_var = np.var(lbp)
            
            # Calculate gradient magnitude
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            grad_mean = np.mean(gradient_magnitude)
            
            # Combine texture features
            if lbp_var > 1000 and grad_mean > 10:
                texture_score = 0.8
            elif lbp_var > 500 and grad_mean > 5:
                texture_score = 0.6
            else:
                texture_score = 0.3
            
            return texture_score
            
        except Exception as e:
            logger.error(f"Texture analysis error: {str(e)}")
            return 0.5
    
    def _calculate_lbp(self, image: np.ndarray, radius: int = 1, n_points: int = 8) -> np.ndarray:
        """
        Calculate Local Binary Pattern for texture analysis
        
        Args:
            image: Grayscale image
            radius: Radius of the LBP
            n_points: Number of points in the LBP
            
        Returns:
            LBP image
        """
        try:
            h, w = image.shape
            lbp = np.zeros((h, w), dtype=np.uint8)
            
            for i in range(radius, h - radius):
                for j in range(radius, w - radius):
                    center = image[i, j]
                    binary_string = ''
                    
                    for k in range(n_points):
                        angle = 2 * np.pi * k / n_points
                        x = i + radius * np.cos(angle)
                        y = j + radius * np.sin(angle)
                        
                        # Bilinear interpolation
                        x1, y1 = int(x), int(y)
                        x2, y2 = x1 + 1, y1 + 1
                        
                        if x2 < h and y2 < w:
                            pixel_value = (x2 - x) * (y2 - y) * image[x1, y1] + \
                                         (x - x1) * (y2 - y) * image[x2, y1] + \
                                         (x2 - x) * (y - y1) * image[x1, y2] + \
                                         (x - x1) * (y - y1) * image[x2, y2]
                            
                            binary_string += '1' if pixel_value > center else '0'
                    
                    lbp[i, j] = int(binary_string, 2)
            
            return lbp
            
        except Exception as e:
            logger.error(f"LBP calculation error: {str(e)}")
            return image
    
    def _analyze_frequency_domain(self, image: np.ndarray) -> float:
        """
        Analyze frequency domain to detect screen replay attacks
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Score indicating likelihood of being real (0-1)
        """
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Apply FFT
            f_transform = np.fft.fft2(gray)
            f_shift = np.fft.fftshift(f_transform)
            magnitude_spectrum = np.log(np.abs(f_shift) + 1)
            
            # Analyze high frequency content
            h, w = magnitude_spectrum.shape
            center_x, center_y = h // 2, w // 2
            
            # Create mask for high frequencies
            mask = np.zeros((h, w))
            radius = min(h, w) // 4
            y, x = np.ogrid[:h, :w]
            mask_circle = (x - center_x) ** 2 + (y - center_y) ** 2 > radius ** 2
            mask[mask_circle] = 1
            
            # Calculate high frequency energy
            high_freq_energy = np.sum(magnitude_spectrum * mask)
            total_energy = np.sum(magnitude_spectrum)
            
            high_freq_ratio = high_freq_energy / (total_energy + 1e-10)
            
            # Real faces typically have more high frequency content
            if high_freq_ratio > 0.3:
                freq_score = 0.8
            elif high_freq_ratio > 0.2:
                freq_score = 0.6
            else:
                freq_score = 0.3
            
            return freq_score
            
        except Exception as e:
            logger.error(f"Frequency domain analysis error: {str(e)}")
            return 0.5
    
    def _analyze_reflections(self, image: np.ndarray) -> float:
        """
        Analyze light reflections to detect 3D masks or photos
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Score indicating likelihood of being real (0-1)
        """
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Find bright spots (potential reflections)
            threshold = np.percentile(gray, 95)  # Top 5% brightest pixels
            bright_spots = gray > threshold
            
            # Count connected components of bright spots
            num_labels, labels = cv2.connectedComponents(bright_spots.astype(np.uint8))
            
            # Analyze spot sizes
            spot_sizes = []
            for i in range(1, num_labels):
                spot_size = np.sum(labels == i)
                spot_sizes.append(spot_size)
            
            if spot_sizes:
                avg_spot_size = np.mean(spot_sizes)
                max_spot_size = np.max(spot_sizes)
                
                # Real faces should have moderate, natural reflections
                if 10 <= avg_spot_size <= 100 and max_spot_size <= 500:
                    reflection_score = 0.8
                elif avg_spot_size <= 200:
                    reflection_score = 0.6
                else:
                    reflection_score = 0.3
            else:
                # No bright spots detected
                reflection_score = 0.4
            
            return reflection_score
            
        except Exception as e:
            logger.error(f"Reflection analysis error: {str(e)}")
            return 0.5
    
    def update_threshold(self, new_threshold: float):
        """Update the anti-spoofing threshold"""
        if 0.0 <= new_threshold <= 1.0:
            self.threshold = new_threshold
            logger.info(f"Anti-spoofing threshold updated to {new_threshold}")
        else:
            logger.warning(f"Invalid threshold value: {new_threshold}")
    
    def enable_anti_spoofing(self, enable: bool = True):
        """Enable or disable anti-spoofing"""
        self.enabled = enable
        logger.info(f"Anti-spoofing {'enabled' if enable else 'disabled'}")
    
    def get_model_info(self) -> dict:
        """Get information about the anti-spoofing model"""
        return {
            'enabled': self.enabled,
            'model_name': self.model_name,
            'model_loaded': self.model_loaded,
            'threshold': self.threshold,
            'input_size': self.input_size
        } 