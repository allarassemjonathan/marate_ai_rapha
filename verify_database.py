#!/usr/bin/env python3
"""
Database Verification Script for Dynamic Column Management System
Run this to check the current state of your database.
"""

import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path so we can import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import get_db_connection
    load_dotenv()
except ImportError as e:
    print(f"❌ Error importing app components: {e}")
    print("Make sure you're running this from the project directory and have installed dependencies.")
    sys.exit(1)

def check_database_structure():
    """Check the current database structure and metadata"""
    print("🔍 Checking Database Structure for Dynamic Column System")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Cannot connect to database. Check your environment variables.")
        return False
    
    cur = conn.cursor()
    
    try:
        # Check if metadata table exists
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'patient_columns_meta'
        """)
        
        if not cur.fetchone():
            print("❌ patient_columns_meta table does not exist")
            print("   Run the Flask app once to create the table automatically")
            return False
        
        print("✅ patient_columns_meta table exists")
        
        # Check patients table structure
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'patients'
            ORDER BY ordinal_position
        """)
        
        print("\n📋 Current patients table structure:")
        patients_columns = cur.fetchall()
        for row in patients_columns:
            nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
            print(f"   {row['column_name']:<25} {row['data_type']:<15} {nullable}")
        
        # Check metadata table content
        cur.execute("""
            SELECT column_name, display_name, data_type, is_visible, is_required, display_order
            FROM patient_columns_meta 
            ORDER BY display_order
        """)
        
        print("\n📊 Column metadata configuration:")
        metadata_rows = cur.fetchall()
        
        if not metadata_rows:
            print("   ⚠️  No metadata found - this indicates first run")
            print("   The metadata will be populated when you start the Flask app")
        else:
            print(f"   {'Column Name':<20} {'Display Name':<20} {'Type':<10} {'Visible':<8} {'Required':<8} {'Order':<5}")
            print("   " + "-" * 80)
            for row in metadata_rows:
                visible = "✓" if row['is_visible'] else "✗"
                required = "✓" if row['is_required'] else "✗"
                print(f"   {row['column_name']:<20} {row['display_name']:<20} {row['data_type']:<10} {visible:<8} {required:<8} {row['display_order']:<5}")
        
        # Check for patients data
        cur.execute("SELECT COUNT(*) as count FROM patients")
        result = cur.fetchone()
        patient_count = result['count']
        
        print(f"\n👥 Patient data: {patient_count} patients in database")
        
        # Check for column mismatches
        print("\n🔍 Checking for inconsistencies:")
        
        # Get actual columns vs metadata columns
        actual_columns = {row['column_name'] for row in patients_columns}
        metadata_columns = {row['column_name'] for row in metadata_rows}
        
        missing_in_metadata = actual_columns - metadata_columns
        missing_in_table = metadata_columns - actual_columns
        
        if missing_in_metadata:
            print(f"   ⚠️  Columns in patients table but not in metadata: {missing_in_metadata}")
        
        if missing_in_table:
            print(f"   ⚠️  Columns in metadata but not in patients table: {missing_in_table}")
        
        if not missing_in_metadata and not missing_in_table:
            print("   ✅ All columns are consistent between table and metadata")
        
        # Check visible columns
        visible_columns = [row['column_name'] for row in metadata_rows if row['is_visible']]
        hidden_columns = [row['column_name'] for row in metadata_rows if not row['is_visible']]
        
        print(f"\n👁️  Visible columns ({len(visible_columns)}): {', '.join(visible_columns)}")
        if hidden_columns:
            print(f"🙈 Hidden columns ({len(hidden_columns)}): {', '.join(hidden_columns)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    finally:
        conn.close()

def test_essential_columns():
    """Test that essential columns are properly protected"""
    print("\n🛡️  Checking Essential Column Protection")
    print("-" * 40)
    
    conn = get_db_connection()
    if not conn:
        return False
    
    cur = conn.cursor()
    
    try:
        essential_columns = ['id', 'name', 'created_at']
        
        cur.execute("SELECT column_name, is_required FROM patient_columns_meta WHERE column_name = ANY(%s)", (essential_columns,))
        results = cur.fetchall()
        
        for col in essential_columns:
            found = False
            for row in results:
                if row['column_name'] == col:
                    found = True
                    status = "✅" if row['is_required'] else "⚠️ "
                    print(f"   {col}: {status}")
                    break
            
            if not found:
                print(f"   {col}: ❌ Missing from metadata")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking essential columns: {e}")
        return False
    
    finally:
        conn.close()

def run_verification():
    """Run all verification checks"""
    print("🧪 Dynamic Column Management System - Database Verification")
    print("=" * 70)
    
    success = True
    
    if not check_database_structure():
        success = False
    
    if not test_essential_columns():
        success = False
    
    print("\n" + "=" * 70)
    
    if success:
        print("🎉 Database verification completed successfully!")
        print("   Your dynamic column system appears to be set up correctly.")
    else:
        print("⚠️  Some issues were found in the database setup.")
        print("   Please review the messages above and fix any issues.")
    
    print("\n💡 Next steps:")
    print("   1. Start the Flask application: flask run")
    print("   2. Run the API test: python test_dynamic_columns_api.py") 
    print("   3. Follow the manual E2E test: test_dynamic_columns_e2e.md")

if __name__ == "__main__":
    run_verification()
