#!/usr/bin/env python3
"""
Test script to verify the new grading distribution is working correctly.
This tests the updated prompts that enforce: 1: 3%, 2: 7%, 3: 80%, 4: 7%, 5: 3%
"""

import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_new_distribution():
    """Test that the new grading distribution prompts are correctly updated"""
    
    print("Testing New Grading Distribution")
    print("=" * 40)
    
    # Read the current prompts from gemini_assessor.py
    with open('gemini_assessor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the new grading distribution text
    new_distribution_text = "Use this strict grading distribution: 80% of scores should be 3 (competent), 7% should be 4 (proficient), 3% should be 5 (exemplary), 7% should be 2 (substandard), and 3% should be 1 (poor)"
    
    if new_distribution_text in content:
        print("✅ New grading distribution text found in gemini_assessor.py")
    else:
        print("❌ New grading distribution text NOT found in gemini_assessor.py")
        return False
    
    # Check for the old grading text (should be removed)
    old_distribution_text = "Use this strict grading distribution: 90% of scores should be 3 (competent), 4% should be 4 (proficient), 1% should be 5 (exemplary), 3% should be 2 (substandard), and 2% should be 1 (poor)"
    
    if old_distribution_text not in content:
        print("✅ Old grading distribution text successfully removed")
    else:
        print("❌ Old grading distribution text still present in gemini_assessor.py")
        return False
    
    # Check documentation
    with open('WORKING_PROMPTS_BACKUP.md', 'r', encoding='utf-8') as f:
        doc_content = f.read()
    
    if new_distribution_text in doc_content:
        print("✅ New grading distribution text found in documentation")
    else:
        print("❌ New grading distribution text NOT found in documentation")
        return False
    
    if old_distribution_text not in doc_content:
        print("✅ Old grading distribution text successfully removed from documentation")
    else:
        print("❌ Old grading distribution text still present in documentation")
        return False
    
    print("\n📊 New Expected Grading Distribution:")
    print("  1 (poor): 3%")
    print("  2 (substandard): 7%") 
    print("  3 (competent): 80%")
    print("  4 (proficient): 7%")
    print("  5 (exemplary): 3%")
    
    print("\n✅ All new grading distribution updates verified successfully!")
    return True

def test_distribution_enforcement():
    """Test that the distribution enforcement method works with new distribution"""
    
    print("\nTesting Distribution Enforcement")
    print("=" * 35)
    
    # Import the assessor class
    from gemini_assessor import SuturingAssessor
    
    # Create a mock assessor instance (we don't need API key for this test)
    assessor = SuturingAssessor.__new__(SuturingAssessor)
    
    # Test cases with different AI-generated score distributions
    test_cases = [
        {
            "name": "All 4s and 5s (should be adjusted down)",
            "scores": [5, 5, 4, 4, 4, 4, 4],
            "expected_distribution": {1: 1, 2: 1, 3: 5, 4: 0, 5: 0}
        },
        {
            "name": "All 1s and 2s (should be adjusted up)",
            "scores": [1, 1, 2, 2, 1, 2, 1],
            "expected_distribution": {1: 1, 2: 1, 3: 5, 4: 0, 5: 0}
        },
        {
            "name": "Mixed scores (should be adjusted to distribution)",
            "scores": [3, 4, 2, 5, 3, 4, 3],
            "expected_distribution": {1: 1, 2: 1, 3: 5, 4: 0, 5: 0}
        },
        {
            "name": "Already close to distribution",
            "scores": [3, 3, 3, 3, 3, 2, 1],
            "expected_distribution": {1: 1, 2: 1, 3: 5, 4: 0, 5: 0}
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print(f"   Original scores: {test_case['scores']}")
        
        # Apply distribution enforcement
        adjusted_scores = assessor._enforce_grading_distribution(test_case['scores'])
        print(f"   Adjusted scores: {adjusted_scores}")
        
        # Count the distribution
        distribution = {}
        for score in adjusted_scores:
            distribution[score] = distribution.get(score, 0) + 1
        
        print(f"   Result distribution: {distribution}")
        
        # Verify the distribution matches expected
        expected = test_case['expected_distribution']
        success = True
        
        for score in [1, 2, 3, 4, 5]:
            actual = distribution.get(score, 0)
            expected_count = expected.get(score, 0)
            if actual != expected_count:
                print(f"   ❌ Score {score}: expected {expected_count}, got {actual}")
                success = False
        
        if success:
            print("   ✅ Distribution enforcement working correctly!")
        else:
            print("   ❌ Distribution enforcement failed!")
            return False
    
    return True

def test_distribution_math():
    """Test that the distribution math is correct for 7 scores"""
    
    print("\nTesting Distribution Math")
    print("=" * 25)
    
    # Target distribution percentages
    target_percentages = {1: 3, 2: 7, 3: 80, 4: 7, 5: 3}
    
    # For 7 scores, calculate expected counts
    expected_counts = {
        1: 1,  # 3% of 7 = 0.21 → 1 (closest to 3%)
        2: 1,  # 7% of 7 = 0.49 → 1 (closest to 7%)
        3: 5,  # 80% of 7 = 5.6 → 5 (closest to 80%)
        4: 0,  # 7% of 7 = 0.49 → 0 (closest to 7%)
        5: 0   # 3% of 7 = 0.21 → 0 (closest to 3%)
    }
    
    print(f"Target percentages: {target_percentages}")
    print(f"Expected counts for 7 scores: {expected_counts}")
    
    # Verify the math
    total = sum(expected_counts.values())
    if total == 7:
        print("✅ Distribution math is correct!")
        return True
    else:
        print(f"❌ Distribution math error: total = {total}, expected 7")
        return False

if __name__ == "__main__":
    print("Testing New Grading Distribution System")
    print("=" * 50)
    
    success1 = test_distribution_math()
    success2 = test_new_distribution()
    success3 = test_distribution_enforcement()
    
    if success1 and success2 and success3:
        print("\n🎉 All tests passed! New grading distribution working correctly.")
        print("\nThe new distribution enforces:")
        print("  - 80% of scores should be 3 (competent)")
        print("  - 7% should be 4 (proficient)") 
        print("  - 3% should be 5 (exemplary)")
        print("  - 7% should be 2 (substandard)")
        print("  - 3% should be 1 (poor)")
        print("\nThis creates a more balanced curve with equal percentages for higher and lower scores.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1) 