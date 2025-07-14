#!/usr/bin/env python3
"""
Test script to verify the polling logic works correctly
"""

import os
from gemini_assessor import VideoDescriber
from config import Config

def test_video_description():
    """Test the video description with polling logic"""
    config = Config()
    api_key = config.get_api_key()
    
    if not api_key:
        print("ERROR: No API key found. Please set your API key in the config.")
        return
    
    # Test with a small video file if available
    test_video = "test_video.mp4"  # You'll need to provide a test video
    
    if not os.path.exists(test_video):
        print(f"Test video {test_video} not found. Please provide a test video file.")
        return
    
    print("Testing VideoDescriber with polling logic...")
    print(f"Video file: {test_video}")
    print(f"File size: {os.path.getsize(test_video) / (1024*1024):.2f} MB")
    
    try:
        describer = VideoDescriber(api_key)
        result = describer.describe_video(test_video)
        
        if 'description' in result:
            print("\nSUCCESS! Video description:")
            print("-" * 50)
            print(result['description'])
        elif 'error' in result:
            print(f"\nERROR: {result['error']}")
            if 'raw_response' in result:
                print(f"Raw response: {result['raw_response']}")
        else:
            print(f"\nUnexpected result: {result}")
            
    except Exception as e:
        print(f"Exception occurred: {e}")

if __name__ == "__main__":
    test_video_description() 