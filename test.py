import psycopg2
import matplotlib
matplotlib.use('Agg')  # ⚠️ À mettre AVANT les imports matplotlib.pyplot
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

import matplotlib
matplotlib.use('Agg')

import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template_string, request
import io, base64
import numpy as np

app = Flask(__name__)

# 🔹 Fonction pour charger les données depuis PostgreSQL
def load_data():
    conn = psycopg2.connect(
        "postgresql://postgres:QUFfTNqAGwNVhBWGbIkkxKfxEyHogGKE@metro.proxy.rlwy.net:56321/railway",
        cursor_factory=RealDictCursor
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM patients")
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    df = pd.DataFrame(rows, columns=columns)
    
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'])
    
    conn.close()
    return df

# 🔹 Page HTML
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Distribution des données</title>
    <style>
        body { 
            font-family: Arial; 
            text-align: center; 
            margin: 40px;
            background: #f5f5f5;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h2 { color: #333; }
        form { margin: 30px 0; }
        select, button { 
            padding: 12px 20px; 
            margin: 10px; 
            font-size: 16px;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        button {
            background: #4CAF50;
            color: white;
            cursor: pointer;
            border: none;
        }
        button:hover { background: #45a049; }
        img { 
            border: 1px solid #ddd; 
            border-radius: 10px;
            margin-top: 20px;
            max-width: 100%;
        }
        .info {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Distribution des données</h2>
        <p>Selectionnez une colonne pour voir sa distribution </p>

        <form method="POST" action="/graph">
            <label><strong>📊 Choisir la colonne :</strong></label><br>
            <select name="column" required>
                <option value="">--Selectionner--</option>
                {% for col in columns %}
                <option value="{{col}}">{{col}}</option>
                {% endfor %}
            </select><br>
            <button type="submit">📈 Générer la distribution</button>
        </form>
        
        {% if graph %}
        <div class="info">
            <strong>{{ column_name }}</strong><br>
        </div>
        <img src="data:image/png;base64,{{ graph }}" width="800">
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    df = load_data()

    #on retourne la page html , la liste des colonnes pour remplir le select 
    #pas de graphe des le lancement de la page
    return render_template_string(HTML_PAGE, columns=df.columns, graph=None)

@app.route("/graph", methods=["POST"])
def graph():

    #Recharge les données (au cas où elles auraient changé)
    df = load_data()

    #recupere la colonne choisie par l'utilisateur dans le formulaire
    column = request.form.get("column")
    
    #Si la colonne choisie n'est pas dans les colonnes de la base de données on envoie un message d'erreur
    if column not in df.columns:
        return "Erreur : colonne invalide", 400
    
    #on a mnt une variable data qui contient notre colonne 
    # ensuite on enleve les valeurs nulles comme non,Nan ou vide
    data = df[column].dropna()
    
    #ensuite on regarde data si ca longueur est nul c'est a dire ne contient rien on envoie un message d'erreur
    if len(data) == 0:
        return "Erreur : aucune donnée dans cette colonne", 400
    
    # 🔹 Informations sur la colonne
    column_type = str(data.dtype)
    unique_count = data.nunique()
    
    plt.figure(figsize=(12, 6))
    
    # 🔹 Traitement selon le type de données

    #Si les valeurs de la colonne sont des nombres alors on va generer un histogramme
    if pd.api.types.is_numeric_dtype(data):
        # Données numériques → Histogramme

        plt.hist(data, bins=30, color='skyblue', edgecolor='black', alpha=0.7)

        #data les données de la colonne choisie que je vais mettre dans l"histogramme
        #bins=30 on vq fqire 30 barres
        #color='skyblue' couleur bleu
        #edgecolor='black' les bordures sont noires
        #alpha=0.7 transparence des barres 70%
        
        plt.title(f'Distribution de {column}')
        plt.xlabel(column)
        plt.ylabel('Fréquence')
        plt.grid(axis='y', alpha=0.3)
        
        
    else:
        # Pour les données qui ne sont pas numeriques

        #On compte les occurences de chaque valeur on selectionne les top 20 des valeurs
        value_counts = data.value_counts().head(20)  

        #value_counts contient les données et leur occurence
        
        plt.barh(range(len(value_counts)), value_counts.values, color='coral')
        #len(value_counts) le nombre de categorie
        #range(len(value_counts) genere les positions
        #value_counts.values la valeur correspondant au nombre d'occurence 
        #color='coral' couleur coral

        plt.yticks(range(len(value_counts)), value_counts.index)
        #Labels de l'axe Y : Remplace [0, 1, 2] par ['Masculin', 'Féminin', 'Autre']

        plt.xlabel('Nombre d\'occurrences')

        plt.title(f'Distribution de {column} (Top 20)')

        #plt.gca().invert_yaxis() récupère l'objet axes sur lequel vous travaillez et va inverser le sens en ;ettant le plus frequent en haut.
        plt.gca().invert_yaxis()
        
        # Ajouter les valeurs sur les barres
        for i, v in enumerate(value_counts.values):
            plt.text(v + max(value_counts.values)*0.01, i, str(v), 
                    va='center', fontweight='bold')
    
    plt.tight_layout()
    
    # 🔹 Conversion en image
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close()
    buf.seek(0)
    
    graph_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    
    return render_template_string(
        HTML_PAGE, 
        columns=df.columns, 
        graph=graph_b64,
        column_name=column,
        column_type=column_type,
        unique_count=unique_count
    )

if __name__ == "__main__":
    app.run(debug=True)