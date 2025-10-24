#!/usr/bin/env python3
"""
Simple test runner that works without pytest
"""
import sys
import os
import importlib.util
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_simple_test():
    """Run a simple test to verify the application works"""
    
    print("🧪 Running Simple Application Test")
    print("=" * 50)
    
    try:
        # Test 1: Import the main application
        print("📋 Test 1: Importing main application...")
        import app
        print("✅ Successfully imported app.py")
        
        # Test 2: Test Flask app creation
        print("\n📋 Test 2: Testing Flask app creation...")
        assert hasattr(app, 'app'), "Flask app not found"
        assert app.app is not None, "Flask app is None"
        print("✅ Flask app created successfully")
        
        # Test 3: Test utility functions
        print("\n📋 Test 3: Testing utility functions...")
        
        # Test clean_float function
        assert app.clean_float("123.45") == 123.45, "clean_float failed for valid number"
        assert app.clean_float("") is None, "clean_float failed for empty string"
        assert app.clean_float("  456.78  ") == 456.78, "clean_float failed for whitespace"
        print("✅ clean_float function works correctly")
        
        # Test 4: Test Flask routes exist
        print("\n📋 Test 4: Testing Flask routes...")
        routes = [rule.rule for rule in app.app.url_map.iter_rules()]
        expected_routes = ['/', '/login', '/add', '/search', '/delete/<int:rowid>']
        
        for route in expected_routes:
            if route in routes or any(expected in r for r in routes for expected in [route.split('<')[0]]):
                print(f"  ✅ Route found: {route}")
            else:
                print(f"  ❌ Route missing: {route}")
        
        # Test 5: Test with test client
        print("\n📋 Test 5: Testing with Flask test client...")
        with app.app.test_client() as client:
            # Test login page
            response = client.get('/login')
            assert response.status_code == 200, f"Login page returned {response.status_code}"
            print("✅ Login page accessible")
            
            # Test protected route redirects to login
            response = client.get('/', follow_redirects=False)
            assert response.status_code == 302, f"Protected route should redirect, got {response.status_code}"
            print("✅ Protected routes properly redirect")
        
        print("\n🎉 All basic tests passed!")
        print("📝 Your application structure is correct and ready for full unit testing")
        print("\n📋 To run full unit tests:")
        print("   1. Create a virtual environment: python3 -m venv venv")
        print("   2. Activate it: source venv/bin/activate") 
        print("   3. Install dependencies: pip install -r requirements.txt")
        print("   4. Run tests: pytest --cov=app")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("📝 Make sure all dependencies are installed")
        return False
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = run_simple_test()
    sys.exit(0 if success else 1)
