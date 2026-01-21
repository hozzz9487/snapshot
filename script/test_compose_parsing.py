#!/usr/bin/env python3
"""
Test script to verify Kotlin Compose parsing improvements
"""

import sys
import pathlib

# Add parent directory to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "py"))

from snapshot import android_parse_code_file

def test_color_kt():
    """Test parsing of Color.kt with val definitions"""
    print("Testing Color.kt parsing...")
    color_file = pathlib.Path("/tmp/test_compose/Color.kt")
    
    if not color_file.exists():
        print("  ⚠️  Color.kt not found, skipping")
        return
    
    result = android_parse_code_file(color_file)
    
    print("  Parsed content:")
    for line in result:
        print(f"    {line}")
    
    # Check if properties were captured
    has_purple80 = any("Purple80" in line for line in result)
    has_pink40 = any("Pink40" in line for line in result)
    
    if has_purple80 and has_pink40:
        print("  ✓ Color properties captured successfully")
    else:
        print("  ❌ Some color properties were not captured")

def test_composable_kt():
    """Test parsing of Composable functions"""
    print("\nTesting QuestionMarkTips.kt parsing...")
    composable_file = pathlib.Path("/tmp/test_compose/QuestionMarkTips.kt")
    
    if not composable_file.exists():
        print("  ⚠️  QuestionMarkTips.kt not found, skipping")
        return
    
    result = android_parse_code_file(composable_file)
    
    print("  Parsed content:")
    for line in result:
        print(f"    {line}")
    
    # Check if Composable functions were captured
    has_question_mark = any("QuestionMarkTips" in line for line in result)
    has_another = any("AnotherComposable" in line for line in result)
    has_constant = any("someConstant" in line for line in result)
    
    if has_question_mark and has_another and has_constant:
        print("  ✓ Composable functions and properties captured successfully")
    else:
        print("  ❌ Some elements were not captured")
        if not has_question_mark:
            print("    - Missing: QuestionMarkTips")
        if not has_another:
            print("    - Missing: AnotherComposable")
        if not has_constant:
            print("    - Missing: someConstant")

if __name__ == "__main__":
    print("=" * 60)
    print("Kotlin Compose Parsing Verification")
    print("=" * 60)
    
    test_color_kt()
    test_composable_kt()
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)
