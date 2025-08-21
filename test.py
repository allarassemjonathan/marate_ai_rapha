import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from psycopg2.extras import RealDictCursor

# Connect to PostgreSQL
conn = psycopg2.connect("postgresql://postgres:QUFfTNqAGwNVhBWGbIkkxKfxEyHogGKE@metro.proxy.rlwy.net:56321/railway", cursor_factory=RealDictCursor)

# Query and load into DataFrame
cur = conn.cursor()
cur.execute("""
    UPDATE patients
    SET
        age_years  = FLOOR(age),
        age_months = FLOOR(0),
        age_days   = FLOOR(0)
    """)
conn.commit()
