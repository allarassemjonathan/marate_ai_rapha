#!/usr/bin/env python3
"""
Test runner script for Marate AI Rapha medical management system
"""
import sys
import subprocess
import os
from pathlib import Path

def run_tests():
    """Run all tests with coverage reporting"""
    
    # Ensure we're in the project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print("🧪 Running Marate AI Rapha Test Suite")
    print("=" * 50)
    
    # Check if pytest is installed
    try:
        import pytest
        print("✅ pytest is available")
    except ImportError:
        print("❌ pytest not found. Installing test dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Run tests with coverage
    test_command = [
        sys.executable, "-m", "pytest",
        "--verbose",
        "--cov=app",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--tb=short",
        "tests/"
    ]
    
    print(f"📋 Running command: {' '.join(test_command)}")
    print("=" * 50)
    
    try:
        result = subprocess.run(test_command, check=False)
        
        if result.returncode == 0:
            print("\n🎉 All tests passed!")
            print("📊 Coverage report generated in htmlcov/")
        else:
            print(f"\n❌ Tests failed with exit code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False
    
    return True

def run_specific_test(test_name):
    """Run a specific test file or test function"""
    
    test_command = [
        sys.executable, "-m", "pytest",
        "--verbose",
        "--tb=short",
        f"tests/{test_name}" if not test_name.startswith("tests/") else test_name
    ]
    
    print(f"🧪 Running specific test: {test_name}")
    print("=" * 50)
    
    try:
        result = subprocess.run(test_command, check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False

def main():
    """Main test runner"""
    
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        success = run_specific_test(test_name)
    else:
        # Run all tests
        success = run_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
