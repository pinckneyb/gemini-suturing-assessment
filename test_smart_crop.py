#!/usr/bin/env python3
"""
Test script for smart cropping functionality
"""

import os
from smart_crop import SmartCropper

def test_smart_crop():
    """Test the smart cropping functionality"""
    print("Testing Smart Cropping Functionality")
    print("=" * 50)
    
    # Initialize smart cropper
    cropper = SmartCropper(confidence_threshold=0.7)
    print(f"Smart cropper initialized with confidence threshold: {cropper.confidence_threshold}")
    
    # Check if we have any test videos
    test_videos = []
    for file in os.listdir('.'):
        if file.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            test_videos.append(file)
    
    if not test_videos:
        print("No video files found for testing.")
        print("To test smart cropping, place a video file in this directory.")
        return
    
    print(f"Found {len(test_videos)} video file(s) for testing:")
    for video in test_videos:
        print(f"  - {video}")
    
    # Test with the first video
    test_video = test_videos[0]
    print(f"\nTesting with video: {test_video}")
    
    # Test detection without cropping
    print("Testing active suture area detection...")
    crop_region = cropper.detect_active_suture_area(test_video, analysis_duration=15)
    
    if crop_region:
        x, y, w, h = crop_region
        print(f"✓ Active suture area detected: x={x}, y={y}, w={w}, h={h}")
        print(f"  Aspect ratio: {w/h:.2f}")
        
        # Check if we have a corresponding final frame
        base_name = os.path.splitext(test_video)[0]
        final_frame = f"{base_name}_final_frame.png"
        
        if os.path.exists(final_frame):
            print(f"\nTesting smart crop on final frame: {final_frame}")
            cropped_path = cropper.crop_final_image(final_frame, test_video)
            
            if cropped_path and os.path.exists(cropped_path):
                print(f"✓ Smart crop successful: {cropped_path}")
                
                # Get file sizes
                original_size = os.path.getsize(final_frame)
                cropped_size = os.path.getsize(cropped_path)
                print(f"  Original size: {original_size:,} bytes")
                print(f"  Cropped size: {cropped_size:,} bytes")
                print(f"  Size reduction: {((original_size - cropped_size) / original_size * 100):.1f}%")
            else:
                print("✗ Smart crop failed")
        else:
            print(f"No final frame found: {final_frame}")
            print("Run the main app first to generate a final frame for testing.")
    else:
        print("✗ No active suture area detected")
        print("This could be due to:")
        print("  - Low activity in the last 15 seconds")
        print("  - Video quality issues")
        print("  - Confidence threshold too high")

if __name__ == "__main__":
    test_smart_crop() 