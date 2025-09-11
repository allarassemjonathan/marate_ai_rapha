import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from psycopg2.extras import RealDictCursor
import matplotlib.ticker as mticker


conn = psycopg2.connect("postgresql://postgres:QUFfTNqAGwNVhBWGbIkkxKfxEyHogGKE@metro.proxy.rlwy.net:56321/railway", cursor_factory=RealDictCursor)

cur = conn.cursor()

cur.execute("SELECT * FROM patients")

rows = cur.fetchall()
columns = [desc[0] for desc in cur.description]

df = pd.DataFrame(rows , columns=columns)

#convertis la colonne des dates en date reelle et pas du simple texte
df['created_at'] = pd.to_datetime(df['created_at'])

#compte le nom de visites par jour
visites_par_jour = df.groupby(df['created_at'].dt.date).size()

# df.groupby permet de regrouper les dates le size permet de les compter
#dt.date permet de ne considerer que les dates et de ne pqs considerer les heures


#generer toutes dates entre la premiere et la derniere date
#df['create_at'] est la colonne qui contient toutes les dates de visite
#.min() prend la plus petite valeur dans cette colonne donc la premiere visite 
toutes_les_dates = pd.date_range(df['created_at'].min().date() , df['created_at'].max().date())

#fait apparaitre des 0 pour les dates qui n'ont pas de visites
#vistes_par_jour contient le nombre de visites par jour mais seulement pour les jours ou il y'a au moins une visite
#si une date existe deja dans visite_par_jour elle garde sa valeur si une date n'existe pas elle est ajoutée avec la velur de 0
visites_par_jour = visites_par_jour.reindex(toutes_les_dates , fill_value=0)

revenu_par_jour = visites_par_jour * 10000

plt.figure(figsize=(10,6))
revenu_par_jour.plot(kind='line' ,color='blue' ,marker='o')
plt.title("Courbe d'evolution du revenu en fonction du temps")
plt.ylabel("Revenu (FCFA)")
plt.xlabel("Date")
plt.tight_layout()
plt.savefig("static/evolution_chiffre_journalier.png")
plt.close()


#genere les consultations par mois en les regroupant et les compte ensuite
consultattion_par_mois = df.groupby(df['created_at'].dt.to_period('M')).size()

#calculer le revenu obtenu
revenu_par_mois = consultattion_par_mois * 10000

#generer toutes les periodes entre le premier mois et le dernier mois
toutes_les_periodes = pd.period_range(df['created_at'].min() ,df['created_at'].max() , freq='M')

#reindexer pour mettre a toutes les periodes vide 0 en revenu
revenu_par_mois = revenu_par_mois.reindex(toutes_les_periodes, fill_value=0)


plt.figure(figsize=(10,6))
revenu_par_mois.plot(kind='line'  , color='blue' , marker ='o')
plt.title("Courbe d'évolution du revenu du cabinet par mois")
plt.xlabel("Mois")
plt.ylabel("Revenu par mois (en FCFA)")
plt.tight_layout()

# Désactiver la notation scientifique sur l'axe Y
plt.gca().yaxis.set_major_formatter(mticker.StrMethodFormatter('{x:,.0f}'))
plt.savefig("static/evolution_chiffe_mensuel.png")
plt.close()



patients_count = df['name'].str.lower().value_counts()[0:8]

patients_count.index = patients_count.index.str.title()

plt.figure(figsize=(10,6))
patients_count.plot(kind='bar' , color='blue')
plt.title("Frequences de visites des patients dans le cabinet")
plt.xlabel("Nom")
plt.ylabel("Frequences de visites")
plt.tight_layout()
plt.savefig("static/frequence_patients.png")
plt.close()
