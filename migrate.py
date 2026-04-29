"""
Migration script: Add multi-tenant clinic support.
Creates clinics table, users table, adds clinic_id to existing tables,
and seeds test data.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from argon2 import PasswordHasher
import os
from dotenv import load_dotenv
import json

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
PEPPER_ENV = os.getenv("PEPPER_ENV")

ph = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,
    parallelism=4,
    hash_len=32,
    salt_len=16
)

def _apply_pepper(password: str) -> str:
    pepper = os.getenv(PEPPER_ENV) if PEPPER_ENV else None
    if pepper:
        return password + pepper
    return password

def hash_password(password: str) -> str:
    return ph.hash(_apply_pepper(password))

def run_migration():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn.autocommit = True
    cur = conn.cursor()

    print("=== Step 1: Create clinics table ===")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clinics (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Seed clinics (idempotent)
    cur.execute("SELECT count(*) as cnt FROM clinics")
    if cur.fetchone()['cnt'] == 0:
        cur.execute("INSERT INTO clinics (name) VALUES ('Clinique Rapha'), ('Hopital Mere Enfant')")
        print("  Inserted 2 clinics")
    else:
        print("  Clinics already exist, skipping")

    print("=== Step 2: Create users table ===")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            clinic_id INTEGER NOT NULL REFERENCES clinics(id),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Seed users (idempotent)
    cur.execute("SELECT count(*) as cnt FROM users")
    if cur.fetchone()['cnt'] == 0:
        users = [
            ('rapha@test.com', hash_password('test1234'), 'Dr Rapha', 'medecins', 1),
            ('mereenfant@test.com', hash_password('test1234'), 'Dr Mere Enfant', 'medecins', 2),
        ]
        for email, pw_hash, name, role, clinic_id in users:
            cur.execute(
                "INSERT INTO users (email, password_hash, name, role, clinic_id) VALUES (%s, %s, %s, %s, %s)",
                (email, pw_hash, name, role, clinic_id)
            )
        print("  Inserted 2 users")
    else:
        print("  Users already exist, skipping")

    print("=== Step 3: Add clinic_id to existing tables ===")
    tables_to_update = ['patients', 'patient_columns_meta', 'column_visibility', 'visits']
    for table in tables_to_update:
        # Check if column already exists
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s AND column_name = 'clinic_id'
        """, (table,))
        if cur.fetchone():
            print(f"  {table}.clinic_id already exists, skipping")
            continue

        cur.execute(f"ALTER TABLE {table} ADD COLUMN clinic_id INTEGER REFERENCES clinics(id)")
        cur.execute(f"UPDATE {table} SET clinic_id = 1 WHERE clinic_id IS NULL")
        cur.execute(f"ALTER TABLE {table} ALTER COLUMN clinic_id SET NOT NULL")
        print(f"  Added clinic_id to {table}")

    print("=== Step 4: Create indexes ===")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_patients_clinic ON patients(clinic_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_visits_clinic ON visits(clinic_id)")

    print("=== Step 5: Fix unique constraints ===")
    # column_visibility: role was UNIQUE, now needs to be (clinic_id, role)
    try:
        cur.execute("ALTER TABLE column_visibility DROP CONSTRAINT IF EXISTS column_visibility_role_key")
        cur.execute("ALTER TABLE column_visibility ADD CONSTRAINT uq_cv_clinic_role UNIQUE (clinic_id, role)")
        print("  Updated column_visibility unique constraint")
    except Exception as e:
        print(f"  column_visibility constraint: {e}")

    # patient_columns_meta: column_name was UNIQUE, now needs to be (clinic_id, column_name)
    try:
        cur.execute("ALTER TABLE patient_columns_meta DROP CONSTRAINT IF EXISTS patient_columns_meta_column_name_key")
        cur.execute("ALTER TABLE patient_columns_meta ADD CONSTRAINT uq_pcm_clinic_col UNIQUE (clinic_id, column_name)")
        print("  Updated patient_columns_meta unique constraint")
    except Exception as e:
        print(f"  patient_columns_meta constraint: {e}")

    print("=== Step 6: Seed data for clinic 2 ===")
    # Duplicate patient_columns_meta for clinic 2
    cur.execute("SELECT count(*) as cnt FROM patient_columns_meta WHERE clinic_id = 2")
    if cur.fetchone()['cnt'] == 0:
        cur.execute("SELECT column_name, display_name, data_type, is_visible, is_required, display_order FROM patient_columns_meta WHERE clinic_id = 1")
        rows = cur.fetchall()
        for row in rows:
            cur.execute("""
                INSERT INTO patient_columns_meta (column_name, display_name, data_type, is_visible, is_required, display_order, clinic_id)
                VALUES (%s, %s, %s, %s, %s, %s, 2)
            """, (row['column_name'], row['display_name'], row['data_type'], row['is_visible'], row['is_required'], row['display_order']))
        print(f"  Duplicated {len(rows)} column meta rows for clinic 2")
    else:
        print("  Clinic 2 column meta already exists")

    # Duplicate column_visibility for clinic 2
    cur.execute("SELECT count(*) as cnt FROM column_visibility WHERE clinic_id = 2")
    if cur.fetchone()['cnt'] == 0:
        cur.execute("SELECT role, columns FROM column_visibility WHERE clinic_id = 1")
        rows = cur.fetchall()
        for row in rows:
            cur.execute(
                "INSERT INTO column_visibility (role, columns, clinic_id) VALUES (%s, %s, 2)",
                (row['role'], json.dumps(row['columns']))
            )
        print(f"  Duplicated {len(rows)} visibility rows for clinic 2")
    else:
        print("  Clinic 2 visibility already exists")

    # Seed patients for clinic 2
    cur.execute("SELECT count(*) as cnt FROM patients WHERE clinic_id = 2")
    if cur.fetchone()['cnt'] == 0:
        seed_patients = [
            ('Aminata Diallo', 'Dr Mere Enfant', 2),
            ('Moussa Keita', 'Dr Mere Enfant', 2),
        ]
        for name, signature, clinic_id in seed_patients:
            cur.execute(
                "INSERT INTO patients (name, signature, created_at, clinic_id) VALUES (%s, %s, CURRENT_DATE, %s)",
                (name, signature, clinic_id)
            )
        print("  Inserted 2 seed patients for clinic 2")
    else:
        print("  Clinic 2 patients already exist")

    cur.close()
    conn.close()
    print("\n=== Migration complete! ===")
    print("Test credentials:")
    print("  rapha@test.com / test1234  (Clinique Rapha)")
    print("  mereenfant@test.com / test1234  (Hopital Mere Enfant)")

if __name__ == '__main__':
    run_migration()
