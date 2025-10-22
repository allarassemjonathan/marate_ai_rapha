import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from psycopg2.extras import RealDictCursor
import matplotlib.ticker as mticker
import plotly.express as px
from flask import Flask, render_template_string, request
import matplotlib.pyplot as plt
import io, base64
import pandas as pd
import sqlite3   

conn = psycopg2.connect("postgresql://postgres:QUFfTNqAGwNVhBWGbIkkxKfxEyHogGKE@metro.proxy.rlwy.net:56321/railway", cursor_factory=RealDictCursor)

cur = conn.cursor()

cur.execute("SELECT * FROM patients")

rows = cur.fetchall()

columns = [desc[0] for desc in cur.description]

df = pd.DataFrame(rows , columns=columns)

# --- 5. Évolution du nombre de nouveaux patients et patients fréquents par mois ---

# Conversion de la colonne de date
df['created_at'] = pd.to_datetime(df['created_at'])

# Séparation des deux types de patients
nouveaux_patients = df[df['new_cases'].str.lower() == 'oui']
patients_frequents = df[df['new_cases'].str.lower() != 'oui']


# Comptage mensuel
nouveaux_patients_mensuel = nouveaux_patients.groupby(nouveaux_patients['created_at'].dt.to_period('M')).size()
patients_frequents_mensuel = patients_frequents.groupby(patients_frequents['created_at'].dt.to_period('M')).size()

# On combine les deux séries dans un DataFrame pour aligner les mois
evolutions_patients = pd.DataFrame({
    'Nouveaux_patients' : nouveaux_patients_mensuel,
    'Patients_frequents' : patients_frequents_mensuel
}).fillna(0)

# Tracé des courbes
fig5,ax5 = plt.subplots(figsize=(8,4))
ax5.plot(
    evolutions_patients.index.astype(str),
    evolutions_patients['Nouveaux_patients'],
    marker='o',color='blue',label='Nouveaux patients'
)
ax5.plot(
    evolutions_patients.index.astype(str),
    evolutions_patients['Patients_frequents'],
    marker='o',color='orange',label='Patients frequents'
)

plt.title("Evolution mensuelle des patients")
plt.xlabel("Mois")
plt.ylabel("Nombre de patients")
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)
plt.xticks(rotation=45,ha='right')
plt.tight_layout()
# Ajout des valeurs sur les points

plt.show()
