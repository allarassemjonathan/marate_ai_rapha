import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from psycopg2.extras import RealDictCursor
import matplotlib.ticker as mticker
import plotly.express as px
from flask import Flask, render_template_string, request, send_file
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

app = Flask(__name__)

# -------------------------------
# 🔹 Simulation des données
# -------------------------------
def load_df_cached():
    data = {
        'created_at': pd.date_range('2024-01-01', periods=12, freq='M'),
        'new_cases': ['oui', 'non'] * 6,
        'medecin_id': [1, 2, 3, 4, 5, 1, 2, 3, 4, 1, 2, 3],
        'montant': [1000, 1500, 900, 1300, 1700, 2000, 1800, 1200, 1500, 2200, 2500, 2700]
    }
    return pd.DataFrame(data)

# -------------------------------
# 🔹 Génération du graphique
# -------------------------------
def build_evolution_chart(buf, option):
    df = load_df_cached()
    df['created_at'] = pd.to_datetime(df['created_at'])

    plt.figure(figsize=(8, 5))

    if option == "patients":
        nouveaux_patients = df[df['new_cases'].str.lower() == 'oui']
        patients_frequents = df[df['new_cases'].str.lower() != 'oui']

        nouveaux_mensuel = nouveaux_patients.groupby(nouveaux_patients['created_at'].dt.to_period('M')).size()
        frequents_mensuel = patients_frequents.groupby(patients_frequents['created_at'].dt.to_period('M')).size()

        evolution = pd.DataFrame({
            'Nouveaux patients': nouveaux_mensuel,
            'Patients fréquents': frequents_mensuel
        }).fillna(0)

        plt.plot(evolution.index.astype(str), evolution['Nouveaux patients'], marker='o', label='Nouveaux patients', color='blue')
        plt.plot(evolution.index.astype(str), evolution['Patients fréquents'], marker='o', label='Patients fréquents', color='orange')
        plt.title("Évolution mensuelle des patients")

    elif option == "medecins":
        evolution = df.groupby(df['created_at'].dt.to_period('M'))['medecin_id'].nunique()
        plt.plot(evolution.index.astype(str), evolution, marker='o', color='green', label='Médecins actifs')
        plt.title("Évolution mensuelle du nombre de médecins")

    elif option == "revenus":
        evolution = df.groupby(df['created_at'].dt.to_period('M'))['montant'].sum()
        plt.plot(evolution.index.astype(str), evolution, marker='o', color='purple', label='Revenus mensuels')
        plt.title("Évolution mensuelle des revenus")

    else:
        raise ValueError("Option inconnue")

    # Mise en forme commune
    plt.xlabel("Mois")
    plt.ylabel("Valeur")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()

# -------------------------------
# 🔹 Routes Flask
# -------------------------------

# Page principale (HTML intégré directement dans le fichier pour simplifier)
@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Test - Graphiques dynamiques</title>
    </head>
    <body>
        <h1>Visualisation dynamique</h1>
        <form action="/graph" method="get">
            <label for="option">Choisissez une option :</label>
            <select name="option" id="option">
                <option value="patients">Évolution des patients</option>
                <option value="medecins">Évolution des médecins</option>
                <option value="revenus">Évolution des revenus</option>
            </select>
            <button type="submit">Afficher le graphique</button>
        </form>

        <hr>
        <p>Choisissez une option dans le menu déroulant pour afficher le graphique correspondant.</p>
    </body>
    </html>
    """
    return render_template_string(html)

# Route qui génère et affiche le graphique
@app.route('/graph')
def graph():
    option = request.args.get('option', 'patients')
    buf = io.BytesIO()
    build_evolution_chart(buf, option)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

# -------------------------------
# 🚀 Lancement de l’application
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
