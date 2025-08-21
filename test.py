import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from psycopg2.extras import RealDictCursor

# Connect to PostgreSQL
conn = psycopg2.connect("postgresql://postgres:QUFfTNqAGwNVhBWGbIkkxKfxEyHogGKE@metro.proxy.rlwy.net:56321/railway", cursor_factory=RealDictCursor)

# Query and load into DataFrame
cur = conn.cursor()
cur.execute("SELECT * FROM patients")
rows = cur.fetchall()
columns = [desc[0] for desc in cur.description]
df = pd.DataFrame(rows, columns=columns)

# Count occurrences of each 'adresse'
adresse_counts = df['adresse'].value_counts()

# Plot
plt.figure(figsize=(10, 6))
adresse_counts.plot(kind='bar', color='seagreen')
plt.title("Nombre de patients par adresse")
plt.xlabel("Adresse")
plt.ylabel("Nombre de patients")
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()

print('Melo la star has modified something in the code')