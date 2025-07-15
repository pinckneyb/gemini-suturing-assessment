#!/usr/bin/env python3
"""
Test script to validate assessment output format
Run this after any changes to ensure the format is still correct
"""

import re
import sys

def validate_assessment_output(output_text):
    """Validate that assessment output follows the correct format"""
    print("Validating assessment output format...")
    
    # Check for duplicate headers
    header_count = output_text.count("SUTURING ASSESSMENT RESULTS")
    if header_count > 1:
        print("❌ ERROR: Duplicate headers found")
        return False
    
    # Check for rubric points (should be 7)
    rubric_pattern = r'\d+\)\s+[^\n]+\n\d+/5\s+(poor|substandard|competent|proficient|exemplary)\n[^\n]+'
    rubric_matches = re.findall(rubric_pattern, output_text, re.IGNORECASE)
    
    if len(rubric_matches) != 7:
        print(f"❌ ERROR: Expected 7 rubric points, found {len(rubric_matches)}")
        return False
    
    # Check for final score
    final_score_pattern = r'Final Score:\s+\d+/5\s+(poor|substandard|competent|proficient|exemplary)'
    if not re.search(final_score_pattern, output_text, re.IGNORECASE):
        print("❌ ERROR: Final score not found or incorrect format")
        return False
    
    # Check for summative comment
    if not re.search(r'Summative Comment:\s+', output_text):
        print("❌ ERROR: Summative comment not found")
        return False
    
    # Check for verbose descriptions (should not be present)
    verbose_indicators = [
        "This video provides",
        "Here is a detailed breakdown",
        "The video shows",
        "```json",
        "timestamps",
        "step-by-step"
    ]
    
    for indicator in verbose_indicators:
        if indicator.lower() in output_text.lower():
            print(f"❌ ERROR: Verbose description found: '{indicator}'")
            return False
    
    print("✅ SUCCESS: Assessment output format is correct!")
    print(f"   - Found {len(rubric_matches)} rubric points")
    print("   - Final score format correct")
    print("   - Summative comment present")
    print("   - No verbose descriptions")
    print("   - No duplicate headers")
    
    return True

def main():
    """Main test function"""
    print("Assessment Format Validator")
    print("=" * 40)
    
    # Example of correct output format
    correct_output = """SUTURING ASSESSMENT RESULTS
Video File: test_video.mp4
Suture Type: Simple Interrupted
==================================================

1) passes needle perpendicular to skin on both sides of skin
3/5 competent
Needle entry and exit angles are appropriate for tissue approximation

2) avoids multiple forceps grasps of skin
4/5 proficient
Single, stable forceps grasps minimize tissue trauma

3) instrument ties with square knots
3/5 competent
Square knots are formed correctly with alternating loops

4) approximates skin with appropriate tension
2/5 substandard
Excessive tension causes tissue puckering

5) places sutures 0.5 - 1.0 centimeters apart
4/5 proficient
Suture spacing is consistent within target range

6) eversion of the skin edges
3/5 competent
Moderate eversion achieved, could be more pronounced

7) economy of time and motion
3/5 competent
Movements are organized with some unnecessary adjustments

Final Score: 3/5 competent

Summative Comment: This demonstrates competent suturing technique with good needle handling and knot tying. Areas for improvement include reducing suture tension to prevent tissue puckering and enhancing skin edge eversion for optimal wound healing.
"""
    
    print("Testing correct format...")
    if validate_assessment_output(correct_output):
        print("\n✅ Test passed: Correct format validation works")
    else:
        print("\n❌ Test failed: Correct format validation broken")
        sys.exit(1)
    
    print("\n" + "=" * 40)
    print("Validation script ready for use!")
    print("Run this script after any changes to ensure format is maintained.")

if __name__ == "__main__":
    main() 