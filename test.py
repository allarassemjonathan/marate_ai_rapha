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



html = """
<html>
<head><title>Stats Patients</title></head>
<body>
    <h2>Sélection du mois</h2>
    <form method="get" action="/">
        <select name="mois" onchange="this.form.submit()">
            {% for m in mois_list %}
                <option value="{{ m }}" {% if m == mois %}selected{% endif %}>{{ m }}</option>
            {% endfor %}
        </select>
    </form>

    <h3>Histogramme</h3>
    <img src="data:image/png;base64,{{ img1 }}" alt="Histogramme"/>
</body>
</html>
"""


def fig_to_base64(fig):
    buf = io.BytesIO() 
    fig.savefig(buf, format="png", bbox_inches="tight") 
    buf.seek(0) 
    return base64.b64encode(buf.getvalue()).decode("utf-8") 

app = Flask(__name__)

@app.route("/",methods=['GET'])
def stat():

    df['signature'] = df['signature'].str.lower().str.title()
    df['created_at'] = pd.to_datetime(df['created_at'])

    #patient c'est le resultat du group by c'est le nombre de patients par medecins le resultat
    medecins = df.groupby([df['created_at'].dt.to_period('M'), 'signature']).size().reset_index(name ="patients")

    #on transforme la date en chaine de caractere
    medecins['mois'] = medecins['created_at'].astype(str)


    mois_list = sorted(medecins['mois'].unique())
    mois = request.args.get("mois", default=mois_list[0])

    df_medecins = medecins[medecins['mois'] == mois].set_index("signature")['patients']
    fig1, ax1 = plt.subplots(figsize=(8,4))
    df_medecins.plot(kind='bar', color='blue', ax=ax1)
    ax1.set_title(f"Nombre de patients par medecins pour {mois}")
    ax1.set_xlabel("Mois")
    ax1.set_ylabel("Nmombre de patients")
    ax1.set_xticks(ax1.get_xticks(), ax1.get_xticklabels(), rotation=45, ha="right")
    img1 = fig_to_base64(fig1)
    plt.close()

    return render_template_string(html, img1=img1, mois=mois, mois_list=mois_list)


if __name__ == "__main__":
    app.run(debug=True)


