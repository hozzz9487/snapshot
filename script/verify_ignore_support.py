#!/usr/bin/env python3
"""
Verification script to test dynamic .gitignore/.cursorignore support in snapshot.py
"""

import os
import sys
import pathlib
import tempfile
import shutil

# Add parent directory to path to import snapshot module
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "py"))

from snapshot import parse_ignore_patterns, is_excluded

def test_parse_ignore_patterns():
    """Test that parse_ignore_patterns correctly reads ignore files"""
    print("Testing parse_ignore_patterns...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = pathlib.Path(tmpdir)
        gitignore = tmppath / ".gitignore"
        
        # Create a test .gitignore
        gitignore.write_text("""
# This is a comment
*.pyc
__pycache__/
build/
.DS_Store

# Another comment
*.log
""")
        
        patterns = parse_ignore_patterns(gitignore)
        
        expected = ["*.pyc", "__pycache__/", "build/", ".DS_Store", "*.log"]
        assert patterns == expected, f"Expected {expected}, got {patterns}"
        print("  ✓ parse_ignore_patterns works correctly")

def test_is_excluded_with_patterns():
    """Test that is_excluded works with various gitignore patterns"""
    print("\nTesting is_excluded with patterns...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = pathlib.Path(tmpdir)
        project_root = tmppath / "test_project"
        project_root.mkdir()
        
        # Create test directory structure
        (project_root / "__pycache__").mkdir()
        (project_root / "build").mkdir()
        (project_root / "src").mkdir()
        (project_root / "src" / "main.py").touch()
        (project_root / "src" / "test.pyc").touch()
        (project_root / ".DS_Store").touch()
        (project_root / "debug.log").touch()
        
        exclude_patterns = ["*.pyc", "__pycache__/", "build/", ".DS_Store", "*.log"]
        
        # Test exclusions
        assert is_excluded(str(project_root / "__pycache__"), str(project_root), exclude_patterns), "__pycache__ should be excluded"
        assert is_excluded(str(project_root / "build"), str(project_root), exclude_patterns), "build/ should be excluded"
        assert is_excluded(str(project_root / ".DS_Store"), str(project_root), exclude_patterns), ".DS_Store should be excluded"
        assert is_excluded(str(project_root / "src" / "test.pyc"), str(project_root), exclude_patterns), "*.pyc should be excluded"
        assert is_excluded(str(project_root / "debug.log"), str(project_root), exclude_patterns), "*.log should be excluded"
        
        # Test non-exclusions
        assert not is_excluded(str(project_root / "src"), str(project_root), exclude_patterns), "src/ should NOT be excluded"
        assert not is_excluded(str(project_root / "src" / "main.py"), str(project_root), exclude_patterns), "main.py should NOT be excluded"
        
        print("  ✓ is_excluded correctly handles gitignore patterns")

def test_integration():
    """Test that the snapshot tool would correctly use .gitignore from target project"""
    print("\nTesting integration scenario...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = pathlib.Path(tmpdir)
        
        # Create a mock Android project
        android_project = tmppath / "MockAndroidApp"
        android_project.mkdir()
        
        # Create .gitignore in the target project
        gitignore = android_project / ".gitignore"
        gitignore.write_text("""
# Android specific
*.apk
*.ap_
*.dex
local.properties

# Secrets
google-services.json
secrets.xml
""")
        
        # Create some files
        (android_project / "app.apk").touch()
        (android_project / "local.properties").touch()
        (android_project / "google-services.json").touch()
        (android_project / "src").mkdir()
        (android_project / "src" / "MainActivity.java").touch()
        
        # Parse the gitignore
        patterns = parse_ignore_patterns(gitignore)
        
        # Verify exclusions work
        assert is_excluded(str(android_project / "app.apk"), str(android_project), patterns), "app.apk should be excluded"
        assert is_excluded(str(android_project / "local.properties"), str(android_project), patterns), "local.properties should be excluded"
        assert is_excluded(str(android_project / "google-services.json"), str(android_project), patterns), "google-services.json should be excluded"
        assert not is_excluded(str(android_project / "src" / "MainActivity.java"), str(android_project), patterns), "MainActivity.java should NOT be excluded"
        
        print("  ✓ Integration test passed: .gitignore from target project is correctly applied")

if __name__ == "__main__":
    print("=" * 60)
    print("Verification Tests for Dynamic Ignore File Support")
    print("=" * 60)
    
    try:
        test_parse_ignore_patterns()
        test_is_excluded_with_patterns()
        test_integration()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
