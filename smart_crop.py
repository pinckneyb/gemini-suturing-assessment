#!/usr/bin/env python3
"""
Smart cropping module for suturing assessment
Detects active suture areas and crops final product images to focus on the relevant region
"""

import cv2
import numpy as np
import os
from typing import Tuple, Optional, List
import logging

class SmartCropper:
    def __init__(self, confidence_threshold: float = 0.7):
        """
        Initialize smart cropper
        
        Args:
            confidence_threshold: Minimum confidence (0.0-1.0) to apply cropping
        """
        self.confidence_threshold = confidence_threshold
        self.logger = logging.getLogger(__name__)
        
    def detect_active_suture_area(self, video_path: str, analysis_duration: int = 15) -> Optional[Tuple[int, int, int, int]]:
        """
        Analyze the last N seconds of video to detect the active suture area
        
        Args:
            video_path: Path to the video file
            analysis_duration: Number of seconds from end to analyze
            
        Returns:
            Tuple of (x, y, width, height) for crop region, or None if detection fails
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self.logger.warning(f"Could not open video: {video_path}")
                return None
                
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if total_frames == 0:
                self.logger.warning("Video has no frames")
                cap.release()
                return None
            
            # Calculate frames to analyze (last N seconds)
            frames_to_analyze = min(int(fps * analysis_duration), total_frames)
            start_frame = max(0, total_frames - frames_to_analyze)
            
            # Initialize detection arrays
            motion_scores = np.zeros((frame_height, frame_width), dtype=np.float32)
            instrument_scores = np.zeros((frame_height, frame_width), dtype=np.float32)
            hand_scores = np.zeros((frame_height, frame_width), dtype=np.float32)
            
            # Analyze frames
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            prev_frame = None
            frame_count = 0
            
            while frame_count < frames_to_analyze:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Convert to grayscale for analysis
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # 1. Motion detection
                if prev_frame is not None:
                    motion = cv2.absdiff(gray, prev_frame)
                    motion_scores += motion.astype(np.float32)
                
                # 2. Instrument detection (simple edge-based approach)
                edges = cv2.Canny(gray, 50, 150)
                instrument_scores += edges.astype(np.float32)
                
                # 3. Hand/skin detection (color-based)
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                # Detect skin tones
                lower_skin = np.array([0, 20, 70], dtype=np.uint8)
                upper_skin = np.array([20, 255, 255], dtype=np.uint8)
                skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
                hand_scores += skin_mask.astype(np.float32)
                
                prev_frame = gray
                frame_count += 1
            
            cap.release()
            
            # Normalize scores
            if frame_count > 0:
                motion_scores /= frame_count
                instrument_scores /= frame_count
                hand_scores /= frame_count
            
            # Combine scores with weights
            combined_score = (
                0.4 * motion_scores +      # Motion is important
                0.4 * instrument_scores +  # Instruments indicate active area
                0.2 * hand_scores          # Hands show where work is happening
            )
            
            # Find the region with highest activity
            crop_region = self._find_best_crop_region(combined_score, frame_width, frame_height)
            
            if crop_region:
                confidence = self._calculate_confidence(combined_score, crop_region)
                if confidence >= self.confidence_threshold:
                    self.logger.info(f"Smart crop detected with confidence: {confidence:.2f}")
                    return crop_region
                else:
                    self.logger.info(f"Smart crop confidence too low: {confidence:.2f} < {self.confidence_threshold}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in smart crop detection: {e}")
            return None
    
    def _find_best_crop_region(self, score_map: np.ndarray, frame_width: int, frame_height: int) -> Optional[Tuple[int, int, int, int]]:
        """
        Find the best 9:16 crop region based on activity scores
        """
        try:
            # Apply Gaussian blur to smooth the score map
            blurred = cv2.GaussianBlur(score_map, (21, 21), 0)
            
            # Find the maximum activity point
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(blurred)
            center_x, center_y = max_loc
            
            # Calculate crop dimensions (9:16 aspect ratio)
            crop_width = min(frame_width, int(frame_height * 9 / 16))
            crop_height = min(frame_height, int(frame_width * 16 / 9))
            
            # Ensure we don't exceed frame boundaries
            crop_width = min(crop_width, frame_width)
            crop_height = min(crop_height, frame_height)
            
            # Calculate crop coordinates centered on the activity
            x1 = max(0, center_x - crop_width // 2)
            y1 = max(0, center_y - crop_height // 2)
            x2 = min(frame_width, x1 + crop_width)
            y2 = min(frame_height, y1 + crop_height)
            
            # Adjust if we hit boundaries
            if x2 == frame_width:
                x1 = max(0, frame_width - crop_width)
            if y2 == frame_height:
                y1 = max(0, frame_height - crop_height)
            
            return (x1, y1, x2 - x1, y2 - y1)
            
        except Exception as e:
            self.logger.error(f"Error finding crop region: {e}")
            return None
    
    def _calculate_confidence(self, score_map: np.ndarray, crop_region: Tuple[int, int, int, int]) -> float:
        """
        Calculate confidence score for the detected crop region
        """
        try:
            x, y, w, h = crop_region
            
            # Get scores within the crop region
            crop_scores = score_map[y:y+h, x:x+w]
            
            # Calculate average score in crop region vs. entire frame
            crop_avg = np.mean(crop_scores)
            frame_avg = np.mean(score_map)
            
            # Confidence based on relative activity
            if frame_avg > 0:
                confidence = min(1.0, float(crop_avg / frame_avg))
            else:
                confidence = 0.0
                
            return confidence
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {e}")
            return 0.0
    
    def crop_final_image(self, image_path: str, video_path: str) -> Optional[str]:
        """
        Crop the final product image to focus on the active suture area
        
        Args:
            image_path: Path to the final product image
            video_path: Path to the original video
            
        Returns:
            Path to the cropped image, or None if cropping failed
        """
        try:
            # Detect the active suture area
            crop_region = self.detect_active_suture_area(video_path)
            
            if crop_region is None:
                self.logger.info("No active suture area detected, using full image")
                return None
            
            # Load and crop the image
            image = cv2.imread(image_path)
            if image is None:
                self.logger.error(f"Could not load image: {image_path}")
                return None
            
            x, y, w, h = crop_region
            cropped = image[y:y+h, x:x+w]
            
            # Save cropped image
            base_path = os.path.splitext(image_path)[0]
            cropped_path = f"{base_path}_cropped.png"
            cv2.imwrite(cropped_path, cropped)
            
            self.logger.info(f"Smart crop applied: {crop_region} -> {cropped_path}")
            return cropped_path
            
        except Exception as e:
            self.logger.error(f"Error in smart cropping: {e}")
            return None 