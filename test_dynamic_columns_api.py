#!/usr/bin/env python3
"""
Automated End-to-End Test for Dynamic Column Management System
Run this script while the Flask server is running to test the API endpoints.
"""

import requests
import json
import sys
import time

# Configuration
BASE_URL = "http://localhost:5000"
SESSION = requests.Session()

def log_test(test_name, status="RUNNING"):
    """Log test status"""
    if status == "RUNNING":
        print(f"🔄 {test_name}...")
    elif status == "PASS":
        print(f"✅ {test_name} - PASSED")
    elif status == "FAIL":
        print(f"❌ {test_name} - FAILED")

def test_login():
    """Test login functionality"""
    log_test("Login Test")
    
    # Try to access protected route without login
    response = SESSION.get(f"{BASE_URL}/api/columns")
    if response.status_code != 302:  # Should redirect to login
        log_test("Login Test", "FAIL")
        return False
    
    # Login with admin credentials
    login_data = {
        'username': 'Dr_Toralta_G_.Josephine',
        'password': 'your_admin_password'  # Replace with actual password
    }
    
    response = SESSION.post(f"{BASE_URL}/login", data=login_data)
    if response.status_code == 200 and 'login' not in response.url:
        log_test("Login Test", "PASS")
        return True
    else:
        log_test("Login Test", "FAIL")
        print(f"   Login failed. Status: {response.status_code}")
        return False

def test_api_columns():
    """Test the /api/columns endpoint"""
    log_test("API Columns Endpoint Test")
    
    response = SESSION.get(f"{BASE_URL}/api/columns")
    
    if response.status_code != 200:
        log_test("API Columns Endpoint Test", "FAIL")
        print(f"   Status code: {response.status_code}")
        return False
    
    try:
        data = response.json()
        if 'visible_columns' in data and 'all_columns' in data:
            log_test("API Columns Endpoint Test", "PASS")
            print(f"   Found {len(data['visible_columns'])} visible columns")
            print(f"   Found {len(data['all_columns'])} total columns")
            return data
        else:
            log_test("API Columns Endpoint Test", "FAIL")
            print(f"   Invalid response format: {data}")
            return False
    except json.JSONDecodeError:
        log_test("API Columns Endpoint Test", "FAIL")
        print("   Invalid JSON response")
        return False

def test_add_column():
    """Test adding a new column"""
    log_test("Add Column Test")
    
    test_column = {
        'column_name': 'test_allergies',
        'display_name': 'Test Allergies',
        'data_type': 'TEXT'
    }
    
    response = SESSION.post(
        f"{BASE_URL}/api/add_column",
        json=test_column,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        try:
            data = response.json()
            if data.get('status') == 'success':
                log_test("Add Column Test", "PASS")
                return True
            else:
                log_test("Add Column Test", "FAIL")
                print(f"   API returned error: {data.get('message')}")
                return False
        except json.JSONDecodeError:
            log_test("Add Column Test", "FAIL")
            print("   Invalid JSON response")
            return False
    else:
        log_test("Add Column Test", "FAIL")
        print(f"   Status code: {response.status_code}")
        return False

def test_toggle_column():
    """Test toggling column visibility"""
    log_test("Toggle Column Visibility Test")
    
    # Toggle the test column we just added
    toggle_data = {'is_visible': False}
    
    response = SESSION.post(
        f"{BASE_URL}/api/toggle_column/test_allergies",
        json=toggle_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        try:
            data = response.json()
            if data.get('status') == 'success':
                log_test("Toggle Column Visibility Test", "PASS")
                return True
            else:
                log_test("Toggle Column Visibility Test", "FAIL")
                print(f"   API returned error: {data.get('message')}")
                return False
        except json.JSONDecodeError:
            log_test("Toggle Column Visibility Test", "FAIL")
            print("   Invalid JSON response")
            return False
    else:
        log_test("Toggle Column Visibility Test", "FAIL")
        print(f"   Status code: {response.status_code}")
        return False

def test_remove_column():
    """Test removing a column"""
    log_test("Remove Column Test")
    
    response = SESSION.delete(f"{BASE_URL}/api/remove_column/test_allergies")
    
    if response.status_code == 200:
        try:
            data = response.json()
            if data.get('status') == 'success':
                log_test("Remove Column Test", "PASS")
                return True
            else:
                log_test("Remove Column Test", "FAIL")
                print(f"   API returned error: {data.get('message')}")
                return False
        except json.JSONDecodeError:
            log_test("Remove Column Test", "FAIL")
            print("   Invalid JSON response")
            return False
    else:
        log_test("Remove Column Test", "FAIL")
        print(f"   Status code: {response.status_code}")
        return False

def test_search_patients():
    """Test the search functionality with dynamic columns"""
    log_test("Search Patients Test")
    
    response = SESSION.get(f"{BASE_URL}/search?q=")
    
    if response.status_code == 200:
        try:
            data = response.json()
            log_test("Search Patients Test", "PASS")
            print(f"   Found {len(data)} patients")
            return True
        except json.JSONDecodeError:
            log_test("Search Patients Test", "FAIL")
            print("   Invalid JSON response")
            return False
    else:
        log_test("Search Patients Test", "FAIL")
        print(f"   Status code: {response.status_code}")
        return False

def test_essential_column_protection():
    """Test that essential columns cannot be deleted"""
    log_test("Essential Column Protection Test")
    
    # Try to delete the 'name' column (essential)
    response = SESSION.delete(f"{BASE_URL}/api/remove_column/name")
    
    if response.status_code == 200:
        try:
            data = response.json()
            if data.get('status') == 'error' and 'essential' in data.get('message', '').lower():
                log_test("Essential Column Protection Test", "PASS")
                return True
            else:
                log_test("Essential Column Protection Test", "FAIL")
                print(f"   Essential column was allowed to be deleted: {data}")
                return False
        except json.JSONDecodeError:
            log_test("Essential Column Protection Test", "FAIL")
            print("   Invalid JSON response")
            return False
    else:
        log_test("Essential Column Protection Test", "FAIL")
        print(f"   Unexpected status code: {response.status_code}")
        return False

def run_all_tests():
    """Run all automated tests"""
    print("🚀 Starting Dynamic Column Management System E2E Tests")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/login", timeout=5)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Flask server. Make sure it's running on localhost:5000")
        return
    
    tests = [
        test_login,
        test_api_columns,
        test_add_column,
        test_toggle_column,
        test_search_patients,
        test_essential_column_protection,
        test_remove_column,  # Run this last to clean up
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            log_test(test.__name__, "FAIL")
            print(f"   Exception: {e}")
            failed += 1
        
        time.sleep(0.5)  # Small delay between tests
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Dynamic column system is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
