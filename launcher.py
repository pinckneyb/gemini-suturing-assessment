#!/usr/bin/env python3
"""
Launcher for Suturing Assessment Tools
Choose between video description and suturing assessment applications
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'google.genai',
        'tkinter',
        'reportlab',
        'PIL'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nPlease install missing packages using:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Main launcher entry point"""
    print("Suturing Assessment Tools")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    print("\nChoose an application:")
    print("1. Video Description Tool (Simple video analysis)")
    print("2. Suturing Assessment Tool (Full suturing evaluation)")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-2): ").strip()
            
            if choice == "1":
                print("\nLaunching Video Description Tool...")
                try:
                    from suturing_assessment_gui import main
                    main()
                except ImportError as e:
                    print(f"Error importing GUI module: {e}")
                    print("Please ensure all files are in the same directory")
                    sys.exit(1)
                break
                
            elif choice == "2":
                print("\nLaunching Suturing Assessment Tool...")
                try:
                    from suturing_assessment_app import main
                    main()
                except ImportError as e:
                    print(f"Error importing assessment module: {e}")
                    print("Please ensure all files are in the same directory")
                    sys.exit(1)
                break
                
            else:
                print("Invalid choice. Please enter 1 or 2.")
                
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"Unexpected error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main() 