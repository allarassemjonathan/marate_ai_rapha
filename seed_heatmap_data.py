"""
Seed realistic patient data with varied timestamps for the activity heatmap demo.
Run once: python seed_heatmap_data.py
"""
import os, random
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

FIRST_NAMES = [
    "Aminata", "Fatoumata", "Mariam", "Awa", "Kadiatou", "Oumou", "Djénéba",
    "Rokia", "Safiatou", "Bintou", "Ibrahim", "Moussa", "Oumar", "Amadou",
    "Sékou", "Mamadou", "Boubacar", "Abdoulaye", "Modibo", "Cheick",
    "Aïssata", "Hawa", "Tenin", "Nana", "Fanta", "Sali", "Djeneba",
    "Youssouf", "Drissa", "Bakary", "Souleymane", "Lassina", "Adama",
]
LAST_NAMES = [
    "Diallo", "Traoré", "Coulibaly", "Keita", "Koné", "Sissoko", "Touré",
    "Sangaré", "Camara", "Bamba", "Dembélé", "Sidibé", "Doumbia", "Konaté",
    "Cissé", "Diarra", "Bagayoko", "Fofana", "Samaké", "Haidara",
]
DOCTORS_CLINIC1 = ["Dr Allarassem", "Dr Koné", "Dr Traoré"]
DOCTORS_CLINIC2 = ["Dr Fatoumata Diallo", "Dr Oumar Sangaré"]
QUARTIERS = [
    "Hamdallaye", "Badalabougou", "Lafiabougou", "Kalaban Coura",
    "Magnambougou", "Sotuba", "Faladiè", "Hippodrome", "Niarela",
    "Quinzambougou", "Djicoroni Para", "Sebenikoro",
]

# Realistic West African diagnoses with weighted probabilities
DIAGNOSES = [
    ("Paludisme", 25),
    ("Infection respiratoire aiguë", 15),
    ("Gastro-entérite", 12),
    ("Hypertension artérielle", 8),
    ("Diabète type 2", 6),
    ("Anémie", 7),
    ("Dermatose", 5),
    ("Infection urinaire", 6),
    ("Traumatisme", 4),
    ("Conjonctivite", 3),
    ("Otite", 3),
    ("Bronchite", 4),
    ("Douleurs abdominales", 5),
    ("Céphalées", 4),
]
DIAG_NAMES = [d[0] for d in DIAGNOSES]
DIAG_WEIGHTS = [d[1] for d in DIAGNOSES]

# Probability weights: (day_of_week, hour) -> relative weight
# 0=Monday ... 6=Sunday
def visit_weight_clinic1(dow, hour):
    """Rapha: busy mornings, moderate afternoons."""
    if dow == 6:  return 0
    if dow == 5:  return 2 if 8 <= hour <= 12 else 0
    if 8 <= hour <= 11:   return 10
    if 12 <= hour <= 13:  return 3
    if 14 <= hour <= 16:  return 7
    if 17 <= hour <= 18:  return 2
    return 0

def visit_weight_clinic2(dow, hour):
    """Mere Enfant: busier afternoons, lighter mornings."""
    if dow == 6:  return 0
    if dow == 5:  return 3 if 9 <= hour <= 13 else 0
    if 8 <= hour <= 10:   return 5
    if 11 <= hour <= 13:  return 4
    if 14 <= hour <= 17:  return 10
    if 18 <= hour <= 19:  return 3
    return 0


def generate_timestamps(n, weeks_back, weight_fn):
    """Generate n timestamps following realistic clinic patterns."""
    now = datetime.now()
    slots = []
    weights = []

    for week_offset in range(weeks_back):
        base = now - timedelta(weeks=week_offset)
        monday = base - timedelta(days=base.weekday())
        for dow in range(7):
            day = monday + timedelta(days=dow)
            for hour in range(7, 20):
                w = weight_fn(dow, hour)
                if w > 0:
                    slots.append((day, hour))
                    weights.append(w)

    chosen = random.choices(slots, weights=weights, k=n)
    timestamps = []
    for day, hour in chosen:
        minute = random.randint(0, 59)
        ts = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        timestamps.append(ts)
    return timestamps


def seed(clinic_id, doctors, n, weight_fn):
    timestamps = generate_timestamps(n=n, weeks_back=8, weight_fn=weight_fn)
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn.autocommit = True
    cur = conn.cursor()

    count = 0
    for ts in timestamps:
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        doctor = random.choice(doctors)
        new_case = random.choice(["oui", "non", "non", "non"])

        diag = random.choices(DIAG_NAMES, weights=DIAG_WEIGHTS, k=1)[0]
        cur.execute(
            """INSERT INTO patients (name, signature, created_at, clinic_id, new_cases, hypothese_de_diagnostique)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (name, doctor, ts, clinic_id, new_case, diag)
        )
        count += 1

    cur.close()
    conn.close()
    print(f"Seeded {count} patients for clinic {clinic_id}")


def backfill_diagnoses():
    """Add diagnoses to existing patients that don't have one."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT id FROM patients WHERE hypothese_de_diagnostique IS NULL OR hypothese_de_diagnostique = ''")
    rows = cur.fetchall()
    for r in rows:
        diag = random.choices(DIAG_NAMES, weights=DIAG_WEIGHTS, k=1)[0]
        cur.execute("UPDATE patients SET hypothese_de_diagnostique = %s WHERE id = %s", (diag, r['id']))
    cur.close()
    conn.close()
    print(f"Backfilled diagnoses for {len(rows)} existing patients")


if __name__ == "__main__":
    backfill_diagnoses()
    seed(clinic_id=1, doctors=DOCTORS_CLINIC1, n=90, weight_fn=visit_weight_clinic1)
    seed(clinic_id=2, doctors=DOCTORS_CLINIC2, n=60, weight_fn=visit_weight_clinic2)
