#!/usr/bin/env python3
"""
Test script to verify Kotlin extension function parsing
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "py"))

from snapshot import android_parse_code_file

def test_extension_functions():
    """Test parsing of Kotlin extension functions"""
    print("Testing Extension Functions...")
    
    test_files = [
        ("/tmp/test_compose/toMd5FileName.kt", "toMd5FileName"),
        ("/tmp/test_compose/ExtensionFunction.kt", "escapeJavaScriptString"),
    ]
    
    all_passed = True
    
    for file_path, expected_func in test_files:
        file = pathlib.Path(file_path)
        if not file.exists():
            print(f"  ⚠️  {file.name} not found, skipping")
            continue
        
        print(f"\n  Testing {file.name}:")
        result = android_parse_code_file(file)
        
        for line in result:
            print(f"    {line}")
        
        if any(expected_func in line for line in result):
            print(f"  ✓ {expected_func} captured successfully")
        else:
            print(f"  ❌ {expected_func} was NOT captured")
            all_passed = False
    
    return all_passed

if __name__ == "__main__":
    print("=" * 60)
    print("Kotlin Extension Function Parsing Test")
    print("=" * 60)
    
    if test_extension_functions():
        print("\n" + "=" * 60)
        print("✅ All extension functions captured!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ Some extension functions were not captured")
        print("=" * 60)
        sys.exit(1)
