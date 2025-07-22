import sqlite3
conn = sqlite3.connect('patients.db')

cols = ['name', 'date_of_birth', 'adresse', 'age', 'date_de_naissance', 'poids', 'taille', 'tension_arterielle', 'temperature', 'hypothese_de_diagnostique', 'bilan', 'ordonnance', 'temps_de_la_visite', 'created_at', 'signature', 'resultat_bilan', 'renseignements_clinique']
vals1 = ('DJERANE LOIC', None,None, 15, None,83, None, None, None, 'PALUDISME', None, None, None, '2025-07-21', None, None, None) 
vals2 = ('Aouaba Maeva', None,None, 2, None,6, None, None, 36.9, 'collique du nourisson', None, 'microlax pinkoo', None, '2025-07-21', 'Dr DJAURY', None, None)
vals3 = ('Jon Jana', None,'Canada', 5, '2020-07-09',None, None, None, None, None, None, None, None, '2025-07-20', None, None, None)
vals4 = ('Haoua Abdramane', None,'Gassi', 1, None,7, None, None, None, None, None, None, None, '2025-07-19', None, None, None)
vals5 = ('Alex', None,'Atrone', 6, '2018-02-08',10, 62, None, 37, 'paludisme et coinfection bactérienne', 'ASLO, GE, BARR', 'paludisme et coinfection bactérienne', 'antipaludique antituberculeux', '2025-07-19', 'Dr A', None, None)
vals6=  ('Luc', None,'Chagoua', 7, '2018-07-19',None, None, None, None, None, None, None, None, '2025-07-19', None, None, None)

placeholders = ', '.join('?' for _ in vals1)
print(placeholders)
columns = ', '.join(cols)
print(cols)

query = f'INSERT INTO patients ({columns}) VALUES ({placeholders})'

print(query)

conn.execute(query, vals6)

conn.commit()
conn.close()





# Date de création	Nom	Date de naissance	Adresse	Age	Poids	Taille	Tension	Température	Hypothèse	Bilan	Conclusion du bilan	Ordonnance	Signature
# 2025-07-21	DJERANE LOIC			15 ans	83 kg				PALUDISME					
# Modifier
# Supprimer
# Détails
# 2025-07-21	DJERANE LOIC			15 ans	83 kg				PALUDISME					
# Modifier
# Supprimer
# Détails
# 2025-07-21	Aouaba Maeva	2025-05-17		2 ans	6 kg			36.9 °C	colique du nourrisson			microlax pinkoo	Dr DJAURY	
# Modifier
# Supprimer
# Détails
# 2025-07-20	Jon Jana	2020-07-09	Canada	5 ans										
# Modifier
# Supprimer
# Détails
# 2025-07-19	Haoua Abdramane		Gassi	1 ans	7 kg									
# Modifier
# Supprimer
# Détails
# 2025-07-19	Alex	2018-02-08	Atrone	6 ans	10 kg	62 m		37 °C	paludisme et coinfection bacté...	ASLO, GE, BARR	paludisme sur un terrain tuber...	antipaludique antituberculeux	Dr A	
# Modifier
# Supprimer
# Détails
# 2025-07-19	Luc	2018-07-19	Chagoua	7 ans										
# Modifier
# Supprimer
# Détails
