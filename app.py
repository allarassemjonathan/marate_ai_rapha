# we will use later .. 
import matplotlib
import base64
matplotlib.use('Agg')  # Must be set before importing pyplot
import matplotlib.pyplot as plt
plt.rcParams['axes.formatter.useoffset'] = False
plt.rcParams['axes.formatter.use_mathtext'] = False
import json
import matplotlib.ticker as mticker
import pandas as pd
import io
from collections import defaultdict
from flask import Flask, render_template, request, jsonify, send_file, session, flash, redirect, url_for, after_this_request
import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from fpdf import FPDF
import os
from dotenv import load_dotenv
from datetime import datetime
import requests
import tempfile
from functools import wraps
import psycopg2
from psycopg2.extras import RealDictCursor
import unicodedata
from flask import g
import time
from argon2 import PasswordHasher, exceptions
import os

import locale
# Optional: to display French month names (if your OS supports it)
try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except:
    pass  # safely ignore if not available on Windows



load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
cabinet = os.getenv("cabinet")  # legacy, replaced by session['clinic_name']
manager = os.getenv("manager")  # legacy, replaced by multi-tenant auth

app = Flask(__name__)


# If modifying these scopes, delete the token.json
SCOPES = ['https://www.googleapis.com/auth/drive.file']

#unicodedata.normalize('NFD', text) sait gerer les caracteres unicodes comme les accents les symboles etc.
#la methode unicodedata('NFD',text) decompose les lettres accentuées en deux parties la lettre de base et l'accent séparé
#for c in ..... on parcourt chaque caractere du texte decomposé
#unicodedata.category donne la categorie unicode du caractere
#Mn = Mark,Nonspacing c'est-à-dire les qccents et diacritiques
#Donc cette condition veut dire de garder seulement les caracteres qui ne sont pas des accents
#''.join() enfin on rassemble tous les caracteres qu'on a gardes pour former une nouvelle chaine

ph = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,
    parallelism=4,
    hash_len=32,
    salt_len=16
)

PEPPER_ENV = os.getenv("PEPPER_ENV")

def _apply_pepper(password: str) -> str:
    pepper = os.getenv(PEPPER_ENV)
    if pepper:
        return password + pepper
    return password

def verify_password(stored_hash: str, candidate_password: str) -> bool:
    candidate = _apply_pepper(candidate_password)
    try:
        return ph.verify(stored_hash, candidate)
    except exceptions.VerifyMismatchError:
        return False
    except exceptions.InvalidHash:
        raise ValueError("Stored password hash has invalid format.")


def safe_text(text):
    return text.encode('latin-1', 'replace').decode('latin-1')

def remove_accents(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def clean_float(value):
    return float(value) if value.strip() != "" else None

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    """Ensure default column meta and visibility exist for the current clinic."""
    clinic_id = session.get('clinic_id')
    if not clinic_id:
        return

    defaults = {
        'medecins': ['created_at', 'name','adresse','phone_number', 'meeting', 'new_cases', 'age','poids','taille','tension_arterielle','temperature','hypothese_de_diagnostique', 'renseignements_clinique', 'bilan','resultat_bilan', 'ordonnance', 'signature'],
        'infirmiers': ['created_at', 'name','poids','taille','tension_arterielle','temperature'],
        'receptionistes': ['created_at', 'name','adresse','phone_number','meeting', 'new_cases','age', 'meeting']
    }
    with get_db_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Check if metadata exists for this clinic
            cur.execute("SELECT COUNT(*) FROM patient_columns_meta WHERE clinic_id = %s", (clinic_id,))
            result = cur.fetchone()
            count = result.get('count', 0) if hasattr(result, 'get') else result[0]

            if count == 0:
                default_columns = [
                    ('id', 'ID', 'SERIAL', True, True, 1),
                    ('name', 'Nom', 'TEXT', True, True, 2),
                    ('adresse', 'Adresse', 'TEXT', True, False, 3),
                    ('age', 'Âge', 'INTEGER', True, False, 4),
                    ('date_of_birth', 'Date de naissance', 'DATE', True, False, 5),
                    ('poids', 'Poids', 'REAL', True, False, 6),
                    ('taille', 'Taille', 'REAL', True, False, 7),
                    ('tension_arterielle', 'Tension artérielle', 'REAL', True, False, 8),
                    ('temperature', 'Température', 'TEXT', True, False, 9),
                    ('hypothese_de_diagnostique', 'Hypothèse de diagnostic', 'TEXT', True, False, 10),
                    ('bilan', 'Bilan', 'TEXT', True, False, 11),
                    ('resultat_bilan', 'Résultat bilan', 'TEXT', True, False, 12),
                    ('signature', 'Signature', 'TEXT', True, False, 13),
                    ('renseignements_clinique', 'Renseignements cliniques', 'TEXT', True, False, 14),
                    ('ordonnance', 'Ordonnance', 'TEXT', True, False, 15),
                    ('created_at', 'Date de création', 'DATE', True, False, 16)
                ]
                for col_name, display_name, data_type, is_visible, is_required, order in default_columns:
                    cur.execute('''
                        INSERT INTO patient_columns_meta
                        (column_name, display_name, data_type, is_visible, is_required, display_order, clinic_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (col_name, display_name, data_type, is_visible, is_required, order, clinic_id))

            # Setup column visibility for this clinic
            for role, cols in defaults.items():
                cur.execute("SELECT 1 FROM column_visibility WHERE role=%s AND clinic_id=%s;", (role, clinic_id))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO column_visibility (role, columns, clinic_id)
                        VALUES (%s, %s, %s);
                    """, (role, json.dumps(cols), clinic_id))
            conn.commit()

# Column management utility functions
def get_visible_columns():
    """Get list of visible columns in display order"""
    print('get_vis_col_py')
    clinic_id = session.get('clinic_id')
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute('''
        SELECT column_name, display_name, data_type
        FROM patient_columns_meta
        WHERE is_visible = TRUE AND clinic_id = %s
        ORDER BY display_order
    ''', (clinic_id,))
    columns = cur.fetchall()
    conn.close()
    return columns

def get_all_columns():
    """Get all columns with their metadata"""
    clinic_id = session.get('clinic_id')
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute('''
        SELECT column_name, display_name, data_type, is_visible, is_required, display_order
        FROM patient_columns_meta
        WHERE clinic_id = %s
        ORDER BY display_order
    ''', (clinic_id,))
    columns = cur.fetchall()
    conn.close()
    return columns

def add_column_to_patients(column_name, data_type):
    """Add a new column to the patients table"""
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    
    # Map data types to PostgreSQL types
    type_mapping = {
        'TEXT': 'TEXT',
        'INTEGER': 'INTEGER',
        'REAL': 'REAL',
        'DATE': 'DATE',
        'BOOLEAN': 'BOOLEAN'
    }
    
    postgres_type = type_mapping.get(data_type, 'TEXT')
    
    try:
        cur.execute(f'ALTER TABLE patients ADD COLUMN {column_name} {postgres_type}')
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding column: {e}")
        conn.close()
        return False

def remove_column_from_patients(column_name):
    """Remove a column from the patients table"""
    # Don't allow removal of essential columns
    essential_columns = ['id', 'name', 'created_at']
    if column_name in essential_columns:
        return False
    
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        cur.execute(f'ALTER TABLE patients DROP COLUMN {column_name}')
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error removing column: {e}")
        conn.close()
        return False

def update_column_visibility(column_name, is_visible):
    """Update column visibility"""
    clinic_id = session.get('clinic_id')
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute('''
        UPDATE patient_columns_meta
        SET is_visible = %s
        WHERE column_name = %s AND clinic_id = %s
    ''', (is_visible, column_name, clinic_id))
    conn.commit()
    conn.close()

def log_file(user_type, action, details=None):
    FILENAME = 'daily_log.txt'
    today_str = datetime.now().strftime('%Y-%m-%d')

    file_exists = os.path.exists(FILENAME)

    if file_exists:
        with open(FILENAME, 'r', encoding='latin-1') as f:
            lines = f.readlines()

        # Check if the first line matches today's date
        if lines and lines[0].strip() == today_str:
            # Append to file
            with open(FILENAME, 'a', encoding='latin-1') as f:
                f.write('\nNouvelle evenement: ' + datetime.now().strftime('%H:%M:%S') + f' {user_type}, {action}, {details}')
            print("Appended to file.")
            return 200
        else:
            print("Date mismatch or empty file — overwriting.")


    # File doesn't exist, is empty, or has a different date — overwrite
    with open(FILENAME, 'w' , encoding='latin-1') as f:
        f.write(today_str + '\n')
        f.write('Nouvelle evenement: ' + datetime.now().strftime('%H:%M:%S') + f' {user_type}, {action}, {details}')
        print('New info')
        return 200
    print("File written with new date.")


# def log_file(user_type, action, details=None):
#     try:
#         conn = get_db_connection()
#         cur = conn.cursor()
#         cur.execute(
#             "INSERT INTO action_logs (user_type, action, details) VALUES (%s, %s, %s)",
#             (user_type, action, details)
#         )
#         conn.commit()
#         conn.close()
#     except Exception as e:
#         print(f"Error logging action: {e}")

# init_db() is now called per-request in index() since it needs clinic_id from session
# on_startup()

print('hello')
app.secret_key = os.environ.get('FLASK_SECRET')
Special_user = ''

# Simple credential storage (in production, use a database)
# CREDENTIALS = {
#     'medecins': os.environ.get('medecins'),
#     'Erik_Toralta': os.environ.get('Erik_Toralta'),
#     'Dr_Mommar_Gueye': os.environ.get('Dr_Mommar_Gueye'), 
#     'receptionistes': os.environ.get('receptionistes'),
#     'infirmiers': os.environ.get('infirmiers'),
#     'Dr_Pape_Amadou_Ndiaye':os.environ.get('Dr_Pape_Amadou_Ndiaye'),
#     'Dr_Fatou_Sarr':os.environ.get('Dr_Fatou_Sarr'), 
#     'Dr_Hassir_Sylla':os.environ.get('Dr_Hassir_Sylla'), 
#     'Sf_Binetou_Coumdal':os.environ.get('Sf_Binetou_Coumdal'), 
#     'Sf_Seynabou_Diop':os.environ.get('Sf_Seynabou_Diop'), 
#     'inf_Sokhna_Safieta_Goumbo':os.environ.get('inf_Sokhna_Safieta_Goumbo'), 
#     'inf_Sidy_Thiam':os.environ.get('inf_Sidy_Thiam'), 
#     'rec_Ndeye_Ware_Samb_Ndioum':os.environ.get('rec_Ndeye_Ware_Samb_Ndioum'), 
#     'rec_Maimouna_Ndiaye': os.environ.get('rec_Maimouna_Ndiaye'),
#     'rec_Arane_Wade':os.environ.get('rec_Arane_Wade'),
#     'bio_Modou_Diome':os.environ.get('bio_Modou_Diome')
# }

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or not session.get('username') or not session.get('clinic_id'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Set up the SMTP server
smtp_server = os.environ.get('SMTP_SERVER')
smtp_port = os.environ.get('SMTP_PORT')
your_email = os.environ.get('EMAIL')
your_password = os.environ.get('CODE')
acteur_inf = os.environ.get('NURSES_EMAIL')
acteur_med = os.environ.get('PHYSI_EMAIL')

def email_reception(firstname, lastname, body, plot, recipient_email):

    # sending the email
    subject = f"Nouveau patient {firstname} {lastname}"
    
    # create the MIME message
    msg = MIMEMultipart()
    msg['From'] = your_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # add an HTML body with the embedded image
    html = f"""
    <html>
    <body>
        <br>
        <p>
        {body}
        </p>
        <br>
        <img style="width: 350px; height: 100px;" src="https://allarassemjonathan.github.io/marate_white.png">
    </body>
    </html>
    """
    msg.attach(MIMEText(html, 'html'))

    if plot:
        # Embed the graph as an inline image
        image = MIMEImage(plot.getvalue(), name="graph.png")
        image.add_header("Content-ID", "<graph>")
        msg.attach(image)


    # Connect to the SMTP server and send the email
    try:
        # Establish connection to Gmail's SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure the connection

        # Log in to the server
        server.login(your_email, your_password)

        # Send the email
        server.send_message(msg)

        print("Email sent successfully!")

    except Exception as e:
        print(f"Error sending email: {e}")

    finally:
        # Close the connection to the server
        server.quit()

    # You could include additional validation for the URL here if needed
    return jsonify(success=True)


# PDF generation using fpdf==1.7.2
class InvoicePDF(FPDF):
    MOIS_FR = {
        "January": "Janvier", "February": "Février", "March": "Mars",
        "April": "Avril", "May": "Mai", "June": "Juin",
        "July": "Juillet", "August": "Août", "September": "Septembre",
        "October": "Octobre", "November": "Novembre", "December": "Décembre"
    }

    def _fmt_currency(self, value):
        return f"{int(value):,} Fcfa".replace(",", " ")

    def header(self):
        # Cyan header band
        self.set_fill_color(255,255,255)
        self.rect(0, 0, 210, 36, 'F')

        # Logos via BytesIO (no temp files)
        try:
            logos = [
                ("https://allarassemjonathan.github.io/solidarite_logo.png", 12, 3, 38),
                ("https://allarassemjonathan.github.io/marate_white.png", 160, 10, 30),
            ]
            for url, x, y, w in logos:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    self.image(io.BytesIO(resp.content), x, y, w)
        except Exception:
            pass

        # Title on the band
        now = datetime.now()
        month_fr = self.MOIS_FR.get(now.strftime('%B'), now.strftime('%B'))
        self.set_y(10)
        self.set_font('Arial', 'B', 15)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, f'FACTURE  -  {month_fr} {now.strftime("%Y")}', align='C')

        self.set_y(58)

    def footer(self):
        self.set_y(-18)
        self.set_draw_color(6, 182, 212)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)
        self.set_font('Arial', '', 7)
        self.set_text_color(140, 140, 140)
        self.cell(63, 5, 'Clinique de la Solidarite', align='L')
        self.cell(63, 5, f'Page {self.page_no()}/{{nb}}', align='C')
        self.cell(63, 5, f'Genere le {datetime.now().strftime("%d/%m/%Y")}', align='R')

    def add_invoice_header(self, meta):
        now = datetime.now()
        month_en = now.strftime('%B')
        month_fr = self.MOIS_FR.get(month_en, month_en)
        year = now.strftime('%Y')
        envoye_a = meta.get('envoye_a', '')

        # Insurance / recipient subtitle
        if envoye_a:
            self.set_font('Arial', '', 10)
            self.set_text_color(80, 80, 80)
            self.cell(0, 7, f"Societe d'assurance : {envoye_a}  -  doit au cabinet Solidarite", align='C', ln=1)
            self.ln(2)

        # Patient info box
        box_x = 10
        box_y = self.get_y()
        box_w = 190
        box_h = 22
        self.set_draw_color(6, 182, 212)
        self.set_line_width(0.3)
        self.rect(box_x, box_y, box_w, box_h, round_corners=True, corner_radius=3, style='D')

        # Row 1: Nom + N Police
        self.set_xy(15, box_y + 3)
        self.set_font('Arial', 'B', 9)
        self.set_text_color(100, 100, 100)
        self.cell(18, 5, 'Nom :')
        self.set_font('Arial', '', 10)
        self.set_text_color(30, 30, 30)
        self.cell(67, 5, meta.get('nom', ''))

        self.set_font('Arial', 'B', 9)
        self.set_text_color(100, 100, 100)
        self.cell(22, 5, 'N Police :')
        self.set_font('Arial', '', 10)
        self.set_text_color(30, 30, 30)
        self.cell(0, 5, meta.get('police', ''), ln=1)

        # Row 2: Prenom + Date
        self.set_x(15)
        self.set_font('Arial', 'B', 9)
        self.set_text_color(100, 100, 100)
        self.cell(18, 5, 'Prenom :')
        self.set_font('Arial', '', 10)
        self.set_text_color(30, 30, 30)
        self.cell(67, 5, meta.get('prenom', ''))

        self.set_font('Arial', 'B', 9)
        self.set_text_color(100, 100, 100)
        self.cell(22, 5, 'Date :')
        self.set_font('Arial', '', 10)
        self.set_text_color(30, 30, 30)
        self.cell(0, 5, now.strftime('%d/%m/%Y'), ln=1)

        self.set_y(box_y + box_h + 6)

    def add_invoice_sections(self, sections, pourcentage_patient):
        total_net = 0
        col_widths = [50, 28, 37, 30, 45]
        table_w = sum(col_widths)

        for section in sections:
            # Section title bar
            self.set_font('Arial', 'B', 11)
            self.set_fill_color(6, 182, 212)
            self.set_text_color(255, 255, 255)
            self.cell(table_w, 9, f'  {section.get("titre", "Section")}', 0, 1, 'L', True)

            # Column headers
            headers = ['Libelle', 'Quantite', 'Montant unit.', '% Assurance', 'Net a payer']
            self.set_font('Arial', 'B', 9)
            self.set_fill_color(230, 248, 250)
            self.set_text_color(60, 60, 60)
            self.set_draw_color(6, 182, 212)
            self.set_line_width(0.2)
            for i, h in enumerate(headers):
                align = 'L' if i == 0 else 'C'
                if i == len(headers) - 1:
                    align = 'R'
                self.cell(col_widths[i], 8, h, 'B', 0, align, True)
            self.ln()

            # Data rows
            self.set_font('Arial', '', 9)
            sous_total = 0

            for idx, article in enumerate(section.get('articles', [])):
                qte = float(article.get('quantite', 1))
                brut = float(article.get('montant', 0))
                net = round(brut * qte * pourcentage_patient / 100)
                sous_total += net
                total_net += net

                # Alternating row fill
                if idx % 2 == 0:
                    self.set_fill_color(255, 255, 255)
                else:
                    self.set_fill_color(245, 247, 250)

                self.set_text_color(30, 30, 30)
                row = [
                    (article.get('libelle', ''), 'L'),
                    (str(int(qte)), 'C'),
                    (self._fmt_currency(brut), 'C'),
                    (f'{int(100 - pourcentage_patient)}%', 'C'),
                    (self._fmt_currency(net), 'R'),
                ]
                for i, (datum, align) in enumerate(row):
                    self.cell(col_widths[i], 8, datum, 0, 0, align, True)
                self.ln()

                # Hairline separator
                y = self.get_y()
                self.set_draw_color(210, 215, 220)
                self.set_line_width(0.15)
                self.line(10, y, 10 + table_w, y)

            # Subtotal row
            self.set_font('Arial', 'B', 10)
            self.set_fill_color(230, 248, 250)
            self.set_draw_color(6, 182, 212)
            self.set_line_width(0.3)
            self.set_text_color(6, 182, 212)
            self.cell(sum(col_widths[:-1]), 9, 'Sous-total  ', 'T', 0, 'R', True)
            self.cell(col_widths[-1], 9, self._fmt_currency(sous_total), 'T', 1, 'R', True)
            self.ln(5)

        # Final total box
        self.ln(3)
        box_w = 130
        box_x = (210 - box_w) / 2
        box_y = self.get_y()
        self.set_fill_color(255, 245, 247)
        self.set_draw_color(220, 20, 60)
        self.set_line_width(0.6)
        self.rect(box_x, box_y, box_w, 14, round_corners=True, corner_radius=3, style='DF')
        self.set_xy(box_x, box_y + 2)
        self.set_font('Arial', 'B', 12)
        self.set_text_color(220, 20, 60)
        self.cell(box_w, 10, f'TOTAL A PAYER : {self._fmt_currency(total_net)}', align='C')
        self.ln(18)


@app.route('/generate_invoice/<int:patient_id>', methods=['POST'])
@login_required
def generate_invoice(patient_id):
    try:
        data = request.get_json()

        if not data or 'meta' not in data or 'sections' not in data:
            return jsonify({'status': 'error', 'message': 'Metadata and sections are required'}), 400

        meta = data['meta']
        sections = data['sections']
        pourcentage_patient = 100 - float(meta.get('pourcentage', 0))  # e.g. 20 if insurance covers 80%

        pdf = InvoicePDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.add_invoice_header(meta)
        pdf.add_invoice_sections(sections, pourcentage_patient)

        tmp_path = tempfile.mktemp(suffix=".pdf")
        pdf.output(tmp_path)

        filename = f"facture_{meta['nom']}_{meta['prenom']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        log_file(
            session.get('user_type'),
            'Facture généré',
            f"Facture généré pour le patient {meta.get('nom')} {meta.get('prenom')}"
        )

        @after_this_request
        def cleanup(response):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            return response

        return send_file(
            tmp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        print(f"Error generating invoice: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


# ── Hospitalization routes ──────────────────────────────────────────

@app.route('/hospitalization', methods=['POST'])
@login_required
def create_hospitalization():
    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        if not patient_id:
            return jsonify({'status': 'error', 'message': 'patient_id requis'}), 400

        treatments = data.get('treatments', [])

        conn = get_db_connection()
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute('''
            INSERT INTO hospitalizations
            (patient_id, date_admission, medecin_traitant, syndrome,
             constante_temperature, constante_ta, constante_fc, constante_poids,
             diagnostic, observation, date_sortie, observations_sortie, created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        ''', (
            patient_id,
            data.get('date_admission') or None,
            data.get('medecin_traitant'),
            data.get('syndrome'),
            data.get('constante_temperature'),
            data.get('constante_ta'),
            data.get('constante_fc'),
            float(data['constante_poids']) if data.get('constante_poids') else None,
            data.get('diagnostic'),
            data.get('observation'),
            data.get('date_sortie') or None,
            data.get('observations_sortie'),
            session.get('username'),
        ))
        hosp_id = cur.fetchone()['id']

        for i, t in enumerate(treatments):
            if not t.get('description', '').strip():
                continue
            cur.execute('''
                INSERT INTO hospitalization_treatments
                (hospitalization_id, ordre, description, fait, fait_par, heure)
                VALUES (%s,%s,%s,%s,%s,%s)
            ''', (
                hosp_id, i + 1, t['description'],
                t.get('fait', False), t.get('fait_par'), t.get('heure'),
            ))

        conn.close()

        log_file(session.get('user_type'), 'Hospitalisation',
                 f"Nouvelle hospitalisation pour patient {patient_id}")

        return jsonify({'status': 'success', 'id': hosp_id})
    except Exception as e:
        print(f"Error creating hospitalization: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/hospitalizations/<int:patient_id>')
@login_required
def list_hospitalizations(patient_id):
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM hospitalizations
        WHERE patient_id = %s ORDER BY date_admission DESC
    ''', (patient_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        for k, v in r.items():
            if hasattr(v, 'isoformat'):
                r[k] = v.isoformat()
    return jsonify(rows)


@app.route('/hospitalization/<int:hosp_id>')
@login_required
def get_hospitalization(hosp_id):
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute('SELECT * FROM hospitalizations WHERE id = %s', (hosp_id,))
    hosp = cur.fetchone()
    if not hosp:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Non trouve'}), 404
    hosp = dict(hosp)
    for k, v in hosp.items():
        if hasattr(v, 'isoformat'):
            hosp[k] = v.isoformat()

    cur.execute('''
        SELECT * FROM hospitalization_treatments
        WHERE hospitalization_id = %s ORDER BY ordre
    ''', (hosp_id,))
    hosp['treatments'] = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(hosp)


@app.route('/hospitalization/<int:hosp_id>', methods=['PUT'])
@login_required
def update_hospitalization(hosp_id):
    try:
        data = request.get_json()
        conn = get_db_connection()
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute('''
            UPDATE hospitalizations SET
                medecin_traitant=%s, syndrome=%s,
                constante_temperature=%s, constante_ta=%s,
                constante_fc=%s, constante_poids=%s,
                diagnostic=%s, observation=%s,
                date_sortie=%s, observations_sortie=%s
            WHERE id=%s
        ''', (
            data.get('medecin_traitant'),
            data.get('syndrome'),
            data.get('constante_temperature'),
            data.get('constante_ta'),
            data.get('constante_fc'),
            float(data['constante_poids']) if data.get('constante_poids') else None,
            data.get('diagnostic'),
            data.get('observation'),
            data.get('date_sortie') or None,
            data.get('observations_sortie'),
            hosp_id,
        ))

        # Replace treatments
        cur.execute('DELETE FROM hospitalization_treatments WHERE hospitalization_id=%s', (hosp_id,))
        for i, t in enumerate(data.get('treatments', [])):
            if not t.get('description', '').strip():
                continue
            cur.execute('''
                INSERT INTO hospitalization_treatments
                (hospitalization_id, ordre, description, fait, fait_par, heure)
                VALUES (%s,%s,%s,%s,%s,%s)
            ''', (
                hosp_id, i + 1, t['description'],
                t.get('fait', False), t.get('fait_par'), t.get('heure'),
            ))

        conn.close()

        log_file(session.get('user_type'), 'Hospitalisation MAJ',
                 f"Hospitalisation {hosp_id} mise a jour")

        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error updating hospitalization: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/hospitalization/<int:hosp_id>/treatments', methods=['PATCH'])
@login_required
def update_treatments(hosp_id):
    user_type = session.get('user_type')
    try:
        data = request.get_json()
        conn = get_db_connection()
        conn.autocommit = True
        cur = conn.cursor()
        for t in data.get('treatments', []):
            cur.execute('''
                UPDATE hospitalization_treatments
                SET fait=%s, fait_par=%s, heure=%s
                WHERE id=%s AND hospitalization_id=%s
            ''', (
                t.get('fait', False),
                t.get('fait_par'),
                t.get('heure'),
                t['id'],
                hosp_id,
            ))
        conn.close()
        log_file(user_type, 'Traitement MAJ',
                 f"Traitements hospitalisation {hosp_id} mis a jour par {session.get('username')}")
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error updating treatments: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/hospitalization/<int:hosp_id>', methods=['DELETE'])
@login_required
def delete_hospitalization(hosp_id):
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute('DELETE FROM hospitalizations WHERE id=%s', (hosp_id,))
    conn.close()
    log_file(session.get('user_type'), 'Hospitalisation supprimee',
             f"Hospitalisation {hosp_id} supprimee")
    return jsonify({'status': 'deleted'})


@app.route('/')
@login_required
def index():
    init_db()  # Restore DB in drive, etc.

    user_type = session.get('user_type')

    print(user_type)
    
    if user_type in ['receptionistes', 'infirmiers']:
        username = user_type[:-1]
    else:
        username = session['username'].replace('_', ' ')

    # Get visible columns for dynamic display
    visible_columns = get_visible_columns()
    role_col = get_visibility_backend(user_type)
    visible_columns = [dict(row) for row in visible_columns]
    print(visible_columns)
    return render_template('index.html',
                         user_type=user_type,
                         username=username,
                         role_col = role_col,
                         visible_columns=visible_columns,
                         cabinet=session.get('clinic_name', ''),
                         manager = manager)


@app.route('/search')
@login_required
def search():
    try:
        print('here in search 1 ')
        q = request.args.get('q', '')
        conn = get_db_connection()
        conn.autocommit = True
        cur = conn.cursor()
        
        # Get visible columns for dynamic query
        visible_columns = get_visible_columns()

        column_names = [col['column_name'] for col in visible_columns]
        print('here is search 2 ', column_names)

        if not column_names:
            return jsonify([])
        
        # Build dynamic SELECT query
        select_columns = ', '.join(column_names)
        print('here is search 3 ', select_columns)
        try:
            print('right before')
            clinic_id = session.get('clinic_id')
            cur.execute(
            "SELECT * FROM patients WHERE name ILIKE %s AND clinic_id = %s;",
            (f'%{q}%', clinic_id)
            )
            print('right after')
        except Exception as e:
            print(e)

        results = cur.fetchall()
        print('here is search 4 ', results)
        conn.close()
        
        # Convert RealDictRow to regular dict for JSON serialization
        formatted_results = []
        for row in results:
            formatted_results.append(dict(row))
    except Exception as e:
        print(e)
        return jsonify(e)
    return jsonify(formatted_results)

@app.route('/distribution')
def show_distribution():
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    columns = ['adresse', 'sexe', 'groupe_sanguin']
    all_values = defaultdict(lambda: defaultdict(int))

    clinic_id = session.get('clinic_id')
    for col in columns:
        cur.execute(f"SELECT {col} FROM patients WHERE clinic_id = %s", (clinic_id,))
        rows = cur.fetchall()
        for (val,) in rows:
            if val:
                all_values[col][val] += 1

    cur.close()
    conn.close()

    return render_template("distribution.html", distributions=all_values)


@app.route('/ipm', methods=['POST'])
@login_required
def ipm_page():
    selected_month = request.form.get('month')
    if not selected_month:
        return "Veuillez sélectionner un mois.", 400

    # Extract year and month
    try:
        year, month = map(int, selected_month.split('-'))
    except ValueError:
        return "Format de mois invalide.", 400

    # Build date range
    start_date = datetime(year, month, 1)
    end_date = datetime(year + (month == 12), (month % 12) + 1, 1)

    # Choose IPM filter (default: 'oui')
    ipm_value = request.form.get('ipm_value', 'non')

    # --- Fetch patients ---
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    clinic_id = session.get('clinic_id')
    cur.execute("""
        SELECT name, created_at
        FROM patients
        WHERE ipm = %s
        AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', %s::timestamp)
        AND clinic_id = %s
        ORDER BY created_at;
    """, (ipm_value, start_date, clinic_id))
    patients = cur.fetchall()
    cur.close()
    conn.close()

    # --- Create PDF ---
    pdf = FPDF()
    pdf.add_page()

    # Add logos
    logo_solidarite = "https://allarassemjonathan.github.io/solidarite_logo.png"
    logo_url = "https://allarassemjonathan.github.io/marate_white.png"

    try:
        pdf.image(logo_url, x=10, y=8, w=60)   # left logo
        pdf.image(logo_solidarite, x=165, y=8, w=25)        # right logo
    except Exception as e:
        print("Logo load error:", e)  # skip gracefully if image not found

    pdf.ln(25)
    pdf.set_font("Arial", 'B', 16)

    # Safe title (convert unsupported chars)
    title = f"Liste des patients IPM - {start_date.strftime('%B %Y')}"
    title_safe = title.encode('latin-1', 'replace').decode('latin-1')
    pdf.ln(10)
    pdf.cell(0, 10, title_safe, ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)

    # Define column widths
    col_widths = [10, 60, 45]
    table_width = sum(col_widths)
    page_width = pdf.w - 2 * pdf.l_margin
    x_start = (page_width - table_width) / 2 + pdf.l_margin

    # --- Table Header ---
    pdf.set_x(x_start)
    pdf.cell(col_widths[0], 10, "N°", 1, 0, "C")
    pdf.cell(col_widths[1], 10, "Nom", 1, 0, "C")
    pdf.cell(col_widths[2], 10, "Date de visite", 1, 1, "C")

    # --- Table Rows ---
    pdf.set_font("Arial", '', 12)
    for i, patient in enumerate(patients, start=1):
        name = patient['name'].encode('latin-1', 'replace').decode('latin-1')
        date_str = patient['created_at'].strftime('%d/%m/%Y') if patient['created_at'] else ''
        pdf.set_x(x_start)
        pdf.cell(col_widths[0], 10, str(i), 1, 0, "C")
        pdf.cell(col_widths[1], 10, name, 1, 0, "L")
        pdf.cell(col_widths[2], 10, date_str, 1, 1, "C")

    # --- No patients message ---
    if not patients:
        pdf.ln(10)
        pdf.cell(0, 10, "Aucun patient IPM pour ce mois.", ln=True, align="C")
    # --- Save to memory ---
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    buffer = io.BytesIO(pdf_bytes)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"patients_ipm_{ipm_value}_{selected_month}.pdf",
        mimetype="application/pdf"
    )

from datetime import datetime, timezone, timedelta # chad timezone attempt
from datetime import date
@app.route('/add', methods=['POST'])
@login_required
def add():
    data = request.get_json() or {}
    print(data)

    # get all the data on columns 
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    clinic_id = session.get('clinic_id')
    cur.execute("SELECT * FROM patient_columns_meta WHERE clinic_id = %s", (clinic_id,))
    rows = cur.fetchall()
    rows = [dict(row) for row in rows]
    print("rows are ", rows)
    lst_cols_int = set(row['column_name'] for row in rows if row['data_type'] == 'INTEGER')
    lst_cols_txt = set(row['column_name'] for row in rows if row['data_type'] == 'TEXT')
    lst_cols_real = set(row['column_name'] for row in rows if row['data_type'] == 'REAL')
    lst_cols_bools = set(row['column_name'] for row in rows if row['data_type'] == 'BOOL')
    lst_cols_date = set(row['column_name'] for row in rows if row['data_type'] == 'DATE')

    print('text', lst_cols_txt)
    print('int', lst_cols_int)
    print('real', lst_cols_real)
    print('bool', lst_cols_bools)
    print('date', lst_cols_date)

    # List of known date fields in the table
    # date_fields = {'name', 'adresse', 'date_of_birth', 'tension_arterielle'} #'taille', 'tension_arterielle', 'temperature', 'hypothese_de_diagnostique', 'bilan', 'resultat_bilan', 'signature', 'renseignements_clinique', 'ordonnance', 'created_at'}

    group_text_date = lst_cols_txt | lst_cols_date

    # Replace empty strings with None for date fields
    cleaned_data = {}
    for k, v in data.items():
        if k in group_text_date and v == '':
            cleaned_data[k] = None
        else:
            cleaned_data[k] = v

    data = cleaned_data
    print(data)
    if not data.get('name'):
        print('issue is here 1 ')
        return jsonify({'status': 'error', 'message': 'Name is required'}), 400

    try:
        gmt_plus1 = timezone(timedelta(hours=1))
        data['created_at'] = datetime.now(gmt_plus1)

        print('this time is good')
        # reading the age
        if 'age_years' in data:
            if data['age_years'] == '':
                years = 0
                data['age_years'] = 0
                print('worked', data['age_years'])
            else:
                years = int(data['age_years'])
                print(years)


            if data['age_months'] == '':
                months = 0
                data['age_months'] = 0
                print('worked', data['age_months'])
            else:
                months = int(data['age_months'])
                print(months)


            print(data['age_days'])
            if data['age_days'] == '':
                days = 0
                data['age_days'] = 0
                print('worked', data['age_days'])
            else:
                print('ever?')
                days = int(str(data["age_days"]))
                print('ever?')
                # print('value', days)

            print(days, months, years)

            # Convert months and days to fractional years
            age_in_years = years + months/12 + days/365

            # Now you can store `age_in_years` in your DB
            data['age'] = round(age_in_years, 10) 
        
        print('what are we doing', data['age'])

        # Fields that should be treated as floats in the DB
        # float_fields = {'age', 'poids', 'taille', 'temperature', 'age_years', 'age_months', 'age_days'}

        float_fields = lst_cols_int | lst_cols_real | lst_cols_bools

        for field in float_fields:
            print(field)
            if field in data:
                if data[field] == '':
                    print(field, 'should be', None)
                    data[field] = None
                else:
                    try:
                        print(field)
                        print(data[field])
                        data[field] = float(data[field])
                    except ValueError:
                        print('issue is here 2 ', field, data[field])
                        return jsonify({'status': 'error', 'message': f'{field} must be a number'}), 400

        # Notify reception if temperature is missing
        if data.get('name') is not None:
            email_reception(
                data['name'], '',
                'Chers infirmiers, vous avez un nouveau patient! Faite-le entrer dès que vous êtes prêt',
                None, acteur_inf
            )

        print(data)
        print(data.items())
        if session['user_type'] == 'medecins':
            if 'username' in session:
                data['signature'] = session['username'].replace('_', ' ')
            else:
                data['signature'] = 'medecins'

        data['clinic_id'] = session.get('clinic_id')

        # Use parameterized query
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ', '.join(['%s'] * len(values))
        print(placeholders, values)
        col_names = ', '.join(columns)

        query = f'INSERT INTO patients ({col_names}) VALUES ({placeholders})'

        conn = get_db_connection()
        conn.autocommit = True
        cur = conn.cursor()
        print(query, values)
        cur.execute(query, values)
        conn.commit()
        conn.close()
        log_file(
            session.get('user_type'),
            'Ajout d\'un patient',
            f"Le patient '{data.get('name')}' a été ajouté"
        )
        return jsonify({'status': 'success'})

    except Exception as e:
        print(e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/delete/<int:rowid>', methods=['DELETE'])
@login_required
def delete(rowid):
    user_type = session.get('user_type')
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    clinic_id = session.get('clinic_id')
    cur.execute('SELECT * FROM patients WHERE id = %s AND clinic_id = %s', (rowid, clinic_id))
    row = cur.fetchall()
    cur.execute('DELETE FROM patients WHERE id = %s AND clinic_id = %s', (rowid, clinic_id))
    conn.commit()
    conn.close()
    log_file(user_type, 'Suppression d\'un patient', f"Le patient avec l'identifiant {rowid} a été supprimé. Voici les infos du patient supprimé {row}")
    return jsonify({'status': 'deleted'})

@app.route('/patient/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    user_type = session.get('user_type')
    log_file(user_type, 'Détails des patients', f"Les détails du patient avec l'identifiant {patient_id} ont été consulté.")

    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    clinic_id = session.get('clinic_id')
    cur.execute('SELECT * FROM patients WHERE id = %s AND clinic_id = %s', (patient_id, clinic_id))
    patients = cur.fetchall()

    if not patients:
        conn.close()
        return "Patient non trouvé", 404

    row_as_dicts = [dict(row) for row in patients]

    print(patients)
    print(row_as_dicts[0])

    name = row_as_dicts[0]['name']
    print('name', name)
    cur.execute('SELECT * FROM patients WHERE name = %s AND clinic_id = %s', (name, clinic_id))
    visits = cur.fetchall()
    print(len(visits))

    row_as_visits = [dict(row) for row in visits]

    hospitalizations = []

    conn.close()
    return render_template('patient.html', visits=row_as_visits, patient=row_as_dicts[0], hospitalizations=hospitalizations, username=session.get('username'), user_type=session.get('user_type'))

@app.route('/get_patient/<int:patient_id>')
@login_required
def get_patient(patient_id):
    user_type = session.get('user_type')
    log_file(user_type, 'Patient sélectionné', f"Patient avec ID {patient_id} selectionné.")

    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    clinic_id = session.get('clinic_id')
    cur.execute('SELECT * FROM patients WHERE id = %s AND clinic_id = %s', (patient_id, clinic_id))
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({'status': 'error', 'message': 'Patient non trouvé'}), 404

    row = dict(row)
    print(session['username'])

    if user_type == 'infirmiers' or user_type == 'receptionistes':
        return jsonify(row)
    if row['signature'] is None:
        return jsonify(row)
    if row and row['signature'] and row['signature'] == session['username'].replace('_', ' '):
        return jsonify(row)
    else:
        return jsonify({'status': 'error', 'message': f"Seul le {row['signature']} a le droit de modifier ce patient."})


@app.route('/update/<int:patient_id>', methods=['PUT'])
@login_required
def update_patient(patient_id):
    data = request.get_json() or {}
    if session['user_type'] == 'medecins':
        data['signature'] = session['username'].replace('_', ' ')
    if not data.get('name'):
        return jsonify({'status': 'error', 'message': 'Name is required'}), 400


    # get all the data on columns 
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    clinic_id = session.get('clinic_id')
    cur.execute("SELECT * FROM patient_columns_meta WHERE clinic_id = %s", (clinic_id,))
    rows = cur.fetchall()
    rows = [dict(row) for row in rows]
    print("rows are ", rows)
    data_fields = set(row['column_name'] for row in rows)

    # Replace empty strings with None for date fields
    cleaned_data = {}
    for k, v in data.items():
        if k in data_fields and v == '':
            cleaned_data[k] = None
        else:
            cleaned_data[k] = v

    print('cleaned data', cleaned_data)
    set_clause = ", ".join([f"{k} = %s" for k in cleaned_data.keys()])
    values = list(cleaned_data.values())
    values.append(patient_id)

    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    values.append(clinic_id)
    cur.execute(f'UPDATE patients SET {set_clause} WHERE id = %s AND clinic_id = %s', values)
    conn.commit()
    conn.close()

    log_file(
        session.get('user_type'),
        'modification patient',
        f"Patient avec ID {patient_id} a été modifié"
    )

    # # get comments from the AI
    # conn_ai = get_db_connection()
    # cur_ai= conn_ai.cursor()
    # cur_ai.execute(f'select * from patients where id = {patient_id}')
    # rows = cur_ai.fetchall()[-1]

    # prompt = rows
    # api_key = os.getenv('api_key')
    # headers = {
    #         "Content-Type": "application/json",
    #         "Authorization": f"Bearer {api_key}"
    #     }
    # payload = {
    #         "model": "gpt-4o-mini",
    #         "messages": [
    #             {
    #                 "role": "user",
    #                 "content": [
    #                     {
    #                         "type": "text",
    #                         "text": 'This patient is coming to the clinic. This is his/her data ' + str(prompt) + " what do you think it the problem. Answer in french. You are talking to a doctor so be precise and very organized in your analysis. Make sentences. This is a small report.This will go into an email so make it sound like one. The physician you are talking to is about to receive this patient. Make an educated guess regarding what he/she could be suffering from if the patient has not been diangosed yet. Use inline tags in order to format well your message. It will be send straight to the person without any formatting "
    #                     }
    #                 ]
    #             }
    #         ],
    #         "max_tokens": 500
    #     }
        
    # try:
    #     response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
    #     if response.status_code == 200:
    #             result = response.json()
    #             print(result['choices'][0]['message']['content'][7:])
    #             email_content = result['choices'][0]['message']['content'][7:]
                 
    # except Exception as e:
    #     print(e)
    
    # email_reception(data['name'], '',email_content, None, acteur_med)
    # email_reception(data['name'], '',email_content, None, 'jonathanjerabe@gmail.com')

    return jsonify({'status': 'success'})


@app.route('/logout')
@login_required
def logout():
    user_type = session.get('user_type')
    log_file(user_type, 'logout', f"L'utilisateur '{user_type}' s'est déconnecté")
    session.clear()  # Clears all session data
    return redirect(url_for('login'))  # Redirects to login page

from twilio.rest import Client

def sms(name, phone, date, time, place, message, code): 
    message = message + f"\nVoila le code: {code}" 
    try: 
        account_sid = os.getenv('account_sid') 
        auth_token = os.getenv('auth_token') 
        client = Client(account_sid, auth_token) 
        msg = client.messages.create( from_='+18666100438', body=message, to=f'+{phone}' ) 
        print(msg.sid) 
        print(message) 
    except Exception as e: 
        print(e)

import random
@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, go to index
    if session.get('logged_in') and session.get('username') and session.get('clinic_id'):
        return redirect(url_for('index', user_type=session.get('user_type')))

    if request.method == 'POST':
        email_input = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        try:
            conn = get_db_connection()
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute("""
                SELECT u.password_hash, u.role, u.name, u.clinic_id, c.name as clinic_name
                FROM users u
                JOIN clinics c ON c.id = u.clinic_id
                WHERE u.email = %s
            """, (email_input,))
            user = cur.fetchone()
            cur.close()
            conn.close()
        except Exception as e:
            print(e)
            flash('Erreur de connection avec la base de donnee')
            return render_template('login.html')

        if not user:
            flash('Cet utilisateur n\'existe pas.')
            return render_template('login.html')

        stored_hash = user['password_hash']
        if verify_password(stored_hash, password):
            session['username'] = user['name']
            session['user_type'] = user['role']
            session['clinic_id'] = user['clinic_id']
            session['clinic_name'] = user['clinic_name']
            session['logged_in'] = True
            log_file(user['name'], 'login', f"L'utilisateur '{user['name']}' s'est connecté avec succès")
            return redirect(url_for('index', user_type=session['user_type']))
        else:
            flash('Email et/ou mot de passe incorrects.')
    return render_template('login.html')


from datetime import datetime, timedelta
from flask import request, session, redirect, url_for, render_template, flash

@app.route('/verify_sms', methods=['GET', 'POST'])
def verify_sms():
    # Ensure the user actually needs verification
    if not session.get('pending_verification') or not session.get('username'):
        flash("Aucune vérification en attente. Veuillez vous connecter.")
        return redirect(url_for('login'))

    username = session['username']

    if request.method == 'POST':
        entered_code = request.form.get('code')

        try:
            conn = get_db_connection()
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(
                "SELECT pending_code FROM users WHERE username = %s",
                (username,)
            )
            result = cur.fetchone()
            cur.close()
            conn.close()
        except Exception as e:
            print("DB error:", e)
            flash("Erreur de connexion à la base de données.")
            return render_template('verify_sms.html')

        # No record found
        if not result:
            flash("Utilisateur introuvable.")
            return render_template('verify_sms.html')

        stored_code = result[0] if isinstance(result, (list, tuple)) else result['pending_code']

        if entered_code == stored_code:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE users 
                    SET last_sms_verification = %s, pending_code = NULL
                    WHERE username = %s
                """, (datetime.now(), username))
                conn.commit()
                cur.close()
                conn.close()
            except Exception as e:
                print("DB update error:", e)
                flash("Erreur lors de la mise à jour de la vérification.")
                return render_template('verify_sms.html')

            # Clear verification flag and log the user in
            session['pending_verification'] = False
            session['logged_in'] = True

            log_file(username, 'sms_verification', f"L'utilisateur '{username}' a confirmé son compte.")
            flash("Vérification réussie !")
            return redirect(url_for('index', user_type=session['user_type']))
        else:
            flash("Code invalide. Veuillez réessayer.")

    return render_template('verify_sms.html')


        # Check credentials
    #     if username_input in CREDENTIALS and CREDENTIALS[username_input] == password:
    #         physicians = {
    #             'Dr_Mommar_Gueye', 'Dr_Pape_Amadou_Ndiaye', 'Dr_Fatou_Sarr', 'Dr_Hassir_Sylla', 'Erik_Toralta'
    #         }

    #         # Always set both username & user_type
    #         if username_input in physicians:
    #             session['username'] = username_input
    #             session['user_type'] = 'medecins'
    #         else:
    #             session['username'] = username_input  # ✅ Added so it's never missing
    #             session['user_type'] = username_input

    #         session['logged_in'] = True
    #         log_file(username_input, 'login', f"L'utilisateur '{username_input}' s'est connecté avec succès")
    #         dic = backend_api_get_columns()
    #         print("just checking", dic["all_columns"])
    #         return redirect(url_for('index', user_type=session['user_type']))
    #     else:
    #         flash('Rôle et/ou mot de passe incorrects.')
    #         log_file(username_input, 'La connexion a échoué', "Failed login attempt")

    # return render_template('login.html')


from io import StringIO
from datetime import date, timedelta
def generate_daily_report(date_of_report=None):
    if date_of_report is None:
        date_of_report = date.today()

    next_day = date_of_report + timedelta(days=1)
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(
        """
        SELECT timestamp, user_type, action, details 
        FROM action_logs
        WHERE timestamp >= %s AND timestamp < %s
        ORDER BY timestamp ASC
        """,
        (date_of_report, next_day)
    )
    logs = cur.fetchall()
    conn.close()

    output = StringIO()
    output.write(f"Action Logs Report for {date_of_report.strftime('%Y-%m-%d')}\n\n")
    for log in logs:
        ts, user, action, details = log
        output.write(f"UserType: {user or 'unknown'} | Action: {action} | Details: {details or ''}\n")

    output.seek(0)
    return output


@app.route('/report')
@login_required
def send_daily_report_email():
    today = date.today()
    # report = generate_daily_report(today)
    report = '/n'.join(open('daily_log.txt', 'r', encoding='latin-1').readlines())

    # Compose email
    subject = f"Daily Action Report for {today.strftime('%Y-%m-%d')}"
    msg = MIMEMultipart()
    msg['From'] = your_email
    msg['To'] =  "jonathanjerabe@gmail.com"
    msg['Subject'] = subject

    print('sending')
    # Attach the report as a text file
    part = MIMEText(report)
    part.add_header('Content-Disposition', 'attachment', filename=f'action_report_{today}.txt')
    msg.attach(part)

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(your_email, your_password)
        server.send_message(msg)
        server.quit()
        return """
        Le rapport journalier des connections au logiciel a été envoyée a l'email jonathanjerabe@gmail.com!
        <br>
        <a href="/">Retour menu <a/>
        """
        
    except Exception as e:
        return f"Failed to send daily report email: {e}"
    
_cache = {}  # keyed by clinic_id

def load_df_cached(ttl=60):
    clinic_id = session.get('clinic_id')
    now = time.time()

    if clinic_id not in _cache or _cache[clinic_id]["df"] is None or (now - _cache[clinic_id]["last_load"]) > ttl:
        _cache[clinic_id] = {"df": load_df(clinic_id), "last_load": now}
    return _cache[clinic_id]["df"]

def load_df(clinic_id=None):
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if clinic_id:
        cur.execute("SELECT * FROM patients WHERE clinic_id = %s", (clinic_id,))
    else:
        cur.execute("SELECT * FROM patients")
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    df = pd.DataFrame(rows, columns=columns)
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'])
    if 'name' in df.columns:
        df['name'] = (df['name'].astype(str).str.strip().apply(remove_accents))

    return df


def nettoyer_donnees(df):
    """Nettoie et normalise les données du DataFrame"""
    
    # 1. Normaliser new_cases
    if 'new_cases' in df.columns:
        df['new_cases'] = df['new_cases'].astype(str).str.lower().str.strip()
        
        # Remplacer toutes les variantes par "oui" ou "non"
        df['new_cases'] = df['new_cases'].replace({
            'ouï': 'oui',
            'Oui ': 'oui',
            'Oui': 'oui',
            'nouveaux': 'oui',
            'nouveau': 'oui',
            'nouveaux cas': 'oui',
            'nouveau cas': 'oui',
            'nouvo': 'oui',
            'yes': 'oui',
            'o': 'oui',
            '': 'Non specifié',
            
            'non': 'non',
            'no': 'non',
            'nn': 'non',
            'ancien': 'non',
            'ancienne': 'non'
        })

        if 'phone_number' in df.columns:
            df['phone_number'] = df['phone_number'].replace({
            '': 'Non specifié',
        })
        if 'ordonnace' in df.columns:
            df['ordonnance'] = df['ordonnance'].replace({
                '': 'Non specifié',
            })
        if 'meeting' in df.columns:
            df['meeting'] = df['meeting'].replace({
            '': 'non',
            'Oui': 'oui',
            'Oui.': 'oui',
            'Randez vous': 'oui',
            'Rendez vous': 'oui'
            })
    # 2. Normaliser la colonne signature (médecins)
    if 'signature' in df.columns:
        df['signature'] = df['signature'].astype(str).str.strip().str.title()
        df['signature'] = df['signature'].replace('', 'Non spécifié')
    
    # 3. Normaliser les adresses
    if 'adresse' in df.columns:
        df['adresse'] = df['adresse'].astype(str).str.split('/').str[0]
        df['adresse'] = df['adresse'].str.replace(r'\d+', '', regex=True)
        df['adresse'] = df['adresse'].str.strip().str.title()
    
    # 4. Conversion des dates
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    
    return df

#Convertir une figure en image web ici on sauvagarde le graphe en memoire pas sur disque et flask l'envoie au navigateur en tant qu'image PNG

def fig_to_png_response():

    #on crée un fichier en memoire (dans la RAM) grace à BytesIO
    #C'est comme un fichier normal mais qui n'existe pas sur disaue on va l'utiliser pour stocker l'image PNG temporairement
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()

    #place le curseur au debut du fichier en memoire(buf)
    buf.seek(0)
    #le navigateur affiche l'iamge générée directement sans jamais l'avoir enregistrée sur disque
    return send_file(buf ,mimetype="image/png")

#transforme un graphique matplotlib en une chaine de texte base64 pour l'afficher dans une page HTML
def fig_to_base64(fig):
    buf = io.BytesIO() #cree un fichier temporaire en memoire(dans la RAM)
    fig.savefig(buf, format="png", bbox_inches="tight") #sauvegarde la figure dans "ce format"
    buf.seek(0) #remet le curseur au debut du fichier(sinon la lecture commence a la fin)
    return base64.b64encode(buf.getvalue()).decode("utf-8") #transforme l'image en texte encode

#un dictionnaire vide au depart qui va permettre de stocker les images générées pour eviter de les recréer a chaque appel
_chart_cache = {} 


#verifie si le graphique existe deja dans _chart_cache
#Si non ou si le cache est trop vieux il regenere le graphique avec generator_func
#Ensuite il retourne l'image en memoire pour que Flask puisse l'envoyer
def get_chart(key, generator_func, ttl=60):
    """Return a cached chart image or regenerate it"""
    now = time.time()
    if key not in _chart_cache or (now - _chart_cache[key]["time"]) > ttl:
        buf = io.BytesIO()
        generator_func(buf) #appelle la fonction qui construit le graphe
        _chart_cache[key] = {"img": buf.getvalue(), "time": now} #stocke l'image + l'heure
    return io.BytesIO(_chart_cache[key]["img"]) #renvoie l'image en memoire


#Ces fonctions utilisent matplotlib + pandas pour creer des graphiques et les sauvegarder dans un buf(memoire)

def build_revenu_journalier_chart(buf):
    df = load_df_cached() #recupere la dataframe(mes donnees)
    visites_par_jour = df.groupby(df['created_at'].dt.date).size()
    toutes_les_dates = pd.date_range(df['created_at'].min().date(), df['created_at'].max().date())
    visites_par_jour = visites_par_jour.reindex(toutes_les_dates, fill_value=0)
    revenu_par_jour = visites_par_jour * 10000
    plt.rcParams['axes.formatter.useoffset'] = False
    plt.rcParams['axes.formatter.use_mathtext'] = False

    plt.figure(figsize=(10,6))
    revenu_par_jour.plot(kind='line', color='blue', marker='o')
    plt.ylabel("Revenu (FCFA)")
    plt.xlabel("Date")
    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()


def build_revenu_mensuel_chart(buf):
    df = load_df_cached()
    consultations_par_mois = df.groupby(df['created_at'].dt.to_period('M')).size()
    revenu_par_mois = consultations_par_mois * 10000
    toutes_les_periodes = pd.period_range(df['created_at'].min(), df['created_at'].max(), freq='M')
    revenu_par_mois = revenu_par_mois.reindex(toutes_les_periodes, fill_value=0)
    plt.rcParams['axes.formatter.useoffset'] = False
    plt.rcParams['axes.formatter.use_mathtext'] = False

    plt.figure(figsize=(10,6))
    revenu_par_mois.plot(kind='line', color='blue', marker='o')
    plt.xlabel("Mois")
    plt.ylabel("Revenu par mois (en FCFA)")
    plt.tight_layout()
    plt.gca().yaxis.set_major_formatter(mticker.StrMethodFormatter('{x:,.0f}'))
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()


def build_frequences_patients_chart(buf):
    df = load_df_cached()
    patients_count = df['name'].str.lower().value_counts()[0:8]
    patients_count.index = patients_count.index.str.title()
    plt.rcParams['axes.formatter.useoffset'] = False
    plt.rcParams['axes.formatter.use_mathtext'] = False

    plt.figure(figsize=(10,6))
    patients_count.plot(kind='bar', color='blue')
    plt.xlabel("Nom")
    plt.ylabel("Fréquences de visites")
    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()


def build_repartition_quartier_chart(buf):
    df = load_df_cached()
    df['adresse'] = df['adresse'].str.split('/').str[0] 
    df['adresse'] = df['adresse'].str.replace('\d+', '', regex=True)  
    df['adresse'] = df['adresse'].str.strip()  
    df['adresse'] = df['adresse'].str.title()  

    adresse_counts = df['adresse'].value_counts()[0:10]

    plt.figure(figsize=(10,6))
    colors=plt.cm.Set3(range(len(adresse_counts)))

    wedges, texts, autotexts = plt.pie(adresse_counts.values, 
                                    labels=adresse_counts.index, 
                                    autopct='%1.1f%%',
                                    colors=colors,
                                    startangle=90)

    plt.title("Nombre de patients par adresse")
    plt.ylabel('')
    plt.xticks(rotation=45 ,ha="right")
    for autotext in autotexts:
        autotext.set_color('black')  # Changement de la couleur du texte
        autotext.set_fontweight('bold')  # Mise en gras du texte

    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()



def build_nouveaux_patients_chart(buf):
    df = load_df_cached()
    df['created_at'] = pd.to_datetime(df['created_at'])

    nouveaux_patients = df[df['new_cases'].str.lower() == 'oui']

    nouveaux_patients = nouveaux_patients.groupby(nouveaux_patients['created_at'].dt.to_period('M')).size()

    plt.figure(figsize=(10,6))
    nouveaux_patients.plot(kind='bar', color='darkblue', width=0.2) # width contrôle l'épaisseur des barres
    plt.title("Nombre de nouveaux patients par mois")
    plt.xlabel("Mois")
    plt.xticks(rotation=45)
    plt.ylabel("Nombre de nouveaux patients")

    for i, value in enumerate(nouveaux_patients):
        plt.text(i, value + 0.1, str(value), ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()


def build_medecins_chart(buf):
    df = load_df_cached()

    df['signature'] = df['signature'].str.strip().str.title()
    df['created_at'] = pd.to_datetime(df['created_at'])
    medecins = df.groupby([df['created_at'].dt.to_period('M'), 'signature']).size().reset_index(name="patients")

    medecins['mois'] = medecins['created_at'].str.astype(str)
    liste_mois = sorted(medecins['mois'].unique())
    mois = request.args.get("mois", default=liste_mois[0])

    df_medecins = medecins[medecins['mois'] == mois].set_index("signature")['patients']
    plt.figure(figsize=(10,6))
    df_medecins.plot(kind='bar', color='blue')
    plt.title("Nombre de patients par malades")
    plt.xlabel("Mois")
    plt.ylabel("Nombre de patients")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()


def build_evolution_patients_chart(buf):
    df = load_df_cached()

    # Conversion des dates
    df['created_at'] = pd.to_datetime(df['created_at'])

    # Séparation des deux types de patients
    nouveaux_patients = df[df['new_cases'].str.lower() == 'oui']
    patients_frequents = df[df['new_cases'].str.lower() != 'oui']

    # Comptage mensuel
    nouveaux_patients_mensuel = nouveaux_patients.groupby(nouveaux_patients['created_at'].dt.to_period('M')).size()
    patients_frequents_mensuel = patients_frequents.groupby(patients_frequents['created_at'].dt.to_period('M')).size()

    # Fusion dans un DataFrame
    evolution_patients = pd.DataFrame({
        'Nouveaux patients': nouveaux_patients_mensuel,
        'Patients fréquents': patients_frequents_mensuel
    }).fillna(0)

    # Création du graphique
    plt.figure(figsize=(10, 6))
    plt.plot(
        evolution_patients.index.astype(str),
        evolution_patients['Nouveaux patients'],
        marker='o', color='blue', label='Nouveaux patients'
    )
    plt.plot(
        evolution_patients.index.astype(str),
        evolution_patients['Patients fréquents'],
        marker='o', color='orange', label='Patients fréquents'
    )

    # ➕ Ajout des valeurs au-dessus des points
    for i, (np_val, pf_val) in enumerate(
        zip(evolution_patients['Nouveaux patients'], evolution_patients['Patients fréquents'])
    ):
        plt.text(i, np_val + 0.2, str(int(np_val)), ha='center', va='bottom',
                 color='blue', fontweight='bold', fontsize=9)
        plt.text(i, pf_val + 0.2, str(int(pf_val)), ha='center', va='bottom',
                 color='orange', fontweight='bold', fontsize=9)

    # Mise en forme
    plt.title("Évolution mensuelle des patients")
    plt.xlabel("Mois")
    plt.ylabel("Nombre de patients")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout() 
    plt.subplots_adjust(top=0.9)   
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()


def build_graph_automatique_chart(buf):
    df = load_df_cached()
    df = nettoyer_donnees(df)
    
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'])

    column = request.form.get("column")

    if column not in df.columns:
        return "Erreur : colonne invalide", 400
    
    data = df[column].dropna()
    
    if len(data) == 0:
        return "Erreur : aucune donnée dans cette colonne", 400
    
    plt.figure(figsize=(12, 6))
    
    if pd.api.types.is_numeric_dtype(data):

        plt.hist(data, bins=30, color='skyblue', edgecolor='black', alpha=0.7)
        plt.title(f'Distribution de {column}')
        plt.xlabel(column)
        plt.ylabel('Fréquence')
        plt.grid(axis='y', alpha=0.3)
        
        
    else:
        # Pour les données qui ne sont pas numeriques

        value_counts = data.value_counts().head(20)  
        
        plt.barh(range(len(value_counts)), value_counts.values, color='coral')
        plt.yticks(range(len(value_counts)), value_counts.index)
        plt.xlabel('Nombre d\'occurrences')
        plt.title(f'Distribution de {column} (Top 20)')
        plt.gca().invert_yaxis()
    
        for i, v in enumerate(value_counts.values):
            plt.text(v + max(value_counts.values)*0.01, i, str(v), 
                    va='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    


#routes flask pour afficher les graphiques seules
#quand tu vas dans l'une des fonctions flask renvoie l'image PNG du graphique(avec cache)
@app.route("/revenu_journalier")
@login_required
def revenu_journalier():
    return send_file(
        get_chart("revenu_journalier", build_revenu_journalier_chart),
        mimetype="image/png"
    )


@app.route("/revenu_mensuel")
@login_required
def revenu_mensuel():
    return send_file(
        get_chart("revenu_mensuel", build_revenu_mensuel_chart),
        mimetype="image/png"
    )


@app.route("/frequences_patients")
@login_required
def frequences_patients():
    return send_file(
        get_chart("frequences_patients", build_frequences_patients_chart),
        mimetype="image/png"
    )


@app.route("/repartition_quartier")
@login_required
def repartition_quartier():
    return send_file(
        get_chart("repartition_quartier",build_repartition_quartier_chart),
        mimetype="image/png"
    )


@app.route("/nouveaux_patients")
@login_required
def nouveaux_patients():
    return send_file(
        get_chart("nouveaux_patients",build_nouveaux_patients_chart),
        mimetype="img/png"
    )

@app.route("/medecins")
@login_required
def medecins():
    return send_file(
        get_chart("medecins",build_medecins_chart),
        mimetype="img/png"
    )

@app.route("/evolution_patients")
@login_required
def evolution_patients():
    return send_file(
        get_chart("evolution_patients",build_evolution_patients_chart),
        mimetype="img/png"
    )

@app.route("/graph_automatique")
@login_required
def graph_automatique():
    return send_file(
        get_chart("graph_automatique",build_graph_automatique_chart),
        mimetype="img/png"
    )

# @app.route("/laboratoire")
# @login_required
# def labo():
#     df = load_df()
#     df_bilan = df[df["bilan"]!=""]
#     df_labo_month = df_bilan.groupby(df['created_at'].dt.to_period('M')).size()
#     toutes_les_periodes = pd.period_range(df['created_at'].min(), df['created_at'].max(), freq='M')
#     def_labo_month = def_labo_month.reindex(toutes_les_periodes, fill_value=0)
    
#     fig9, ax9 = plt.subplots(figsize=(8, 4))
#     def_labo_month.plot(kind="line", marker="o", color="blue", ax=ax9)
#     ax9.set_title("Evolution des revenus mensuels")
#     ax9.set_ylabel("Revenu (FCFA)")
#     ax9.set_xlabel("Mois")
#     ax9.yaxis.set_major_formatter(mticker.StrMethodFormatter('{x:,.0f}'))
#     img9 = fig_to_base64(fig9)
#     plt.close(fig9)

    


@app.route("/stat", methods=['GET','POST'])
@login_required
def rapport():
    df = load_df()
    df['created_at'] = pd.to_datetime(df['created_at'])

    chart_data = {}
    list_mois = []
    mois = None
    column_name = None

    # --- 1. Revenu journalier ---
    if 'created_at' in df.columns:
        visites_par_jour = df.groupby(df['created_at'].dt.date).size()
        toutes_les_dates = pd.date_range(df['created_at'].min().date(), df['created_at'].max().date())
        visites_par_jour = visites_par_jour.reindex(toutes_les_dates, fill_value=0)
        revenu_par_jour = visites_par_jour * 10000
        chart_data['dailyRevenue'] = {
            'labels': [str(d.date()) for d in toutes_les_dates],
            'values': revenu_par_jour.tolist()
        }

    # --- 2. Revenu mensuel ---
    if 'created_at' in df.columns:
        consultations_par_mois = df.groupby(df['created_at'].dt.to_period('M')).size()
        revenu_par_mois = consultations_par_mois * 10000
        toutes_les_periodes = pd.period_range(df['created_at'].min(), df['created_at'].max(), freq='M')
        revenu_par_mois = revenu_par_mois.reindex(toutes_les_periodes, fill_value=0)
        chart_data['monthlyRevenue'] = {
            'labels': [str(p) for p in toutes_les_periodes],
            'values': revenu_par_mois.tolist()
        }

    # --- 3. Fréquences patients ---
    if 'name' in df.columns:
        patients_count = df['name'].str.lower().value_counts()[0:8]
        patients_count.index = patients_count.index.str.title()
        chart_data['recurringPatients'] = {
            'labels': patients_count.index.tolist(),
            'values': patients_count.values.tolist()
        }

    # --- 4. Distribution par quartier ---
    if 'adresse' in df.columns:
        df['adresse'] = df['adresse'].str.split('/').str[0]
        df['adresse'] = df['adresse'].str.replace(r'\d+', '', regex=True)
        df['adresse'] = df['adresse'].str.strip()
        df['adresse'] = df['adresse'].str.title()
        adresse_counts = df['adresse'].value_counts()[0:10]
        if not adresse_counts.empty:
            chart_data['neighborhoodDistribution'] = {
                'labels': adresse_counts.index.tolist(),
                'values': adresse_counts.values.tolist()
            }

    # --- 5. Nouveaux patients ---
    if 'new_cases' in df.columns:
        nouveaux_patients = df[df['new_cases'].str.lower() == 'oui']
        nouveaux_par_mois = nouveaux_patients.groupby(nouveaux_patients['created_at'].dt.to_period('M')).size()
        if not nouveaux_par_mois.empty:
            chart_data['newPatientsPerMonth'] = {
                'labels': [str(p) for p in nouveaux_par_mois.index],
                'values': nouveaux_par_mois.values.tolist()
            }

    # --- 6. Patients par médecins (all months for client-side switching) ---
    if 'signature' in df.columns:
        df['signature'] = df['signature'].str.lower().str.title()
        df = df.dropna(subset=['signature'])
        df = df[df['signature'].str.strip() != ""]
        medecins = df.groupby([df['created_at'].dt.to_period('M'), 'signature']).size().reset_index(name="patients")
        if not medecins.empty:
            medecins['mois'] = medecins['created_at'].astype(str)
            list_mois = sorted(medecins['mois'].unique())
            mois = request.args.get("mois", default=list_mois[0])
            by_month = {}
            for m in list_mois:
                df_m = medecins[medecins['mois'] == m].set_index("signature")['patients'].sort_values(ascending=True)
                by_month[m] = {
                    'labels': df_m.index.tolist(),
                    'values': df_m.values.tolist()
                }
            chart_data['patientsPerDoctor'] = {
                'months': list_mois,
                'defaultMonth': mois,
                'byMonth': by_month
            }

    # --- 7. Evolution des patients ---
    df['created_at'] = pd.to_datetime(df['created_at'])
    nouveaux_patients = df[df['new_cases'].str.lower() == 'oui']
    patients_frequents = df[df['new_cases'].str.lower() != 'oui']
    nouveaux_patients_mensuel = nouveaux_patients.groupby(nouveaux_patients['created_at'].dt.to_period('M')).size()
    patients_frequents_mensuel = patients_frequents.groupby(patients_frequents['created_at'].dt.to_period('M')).size()
    evolutions_patients = pd.DataFrame({
        'Nouveaux patients': nouveaux_patients_mensuel,
        'Patients frequents': patients_frequents_mensuel
    }).fillna(0)
    chart_data['patientEvolution'] = {
        'labels': [str(p) for p in evolutions_patients.index],
        'newPatients': evolutions_patients['Nouveaux patients'].astype(int).tolist(),
        'recurringPatients': evolutions_patients['Patients frequents'].astype(int).tolist()
    }

    # --- 8. Distribution dynamique ---
    df = nettoyer_donnees(df)
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'])

    column = request.form.get("column")
    if column and column in df.columns:
        column_name = column
        data = df[column].dropna()
        if len(data) > 0:
            if pd.api.types.is_numeric_dtype(data):
                counts, bin_edges = pd.cut(data, bins=30, retbins=True)
                hist_values = data.groupby(counts).count()
                chart_data['distribution'] = {
                    'type': 'histogram',
                    'labels': [f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}" for i in range(len(bin_edges)-1)],
                    'values': hist_values.values.tolist(),
                    'columnName': column
                }
            else:
                value_counts = data.value_counts().head(20)
                chart_data['distribution'] = {
                    'type': 'categorical',
                    'labels': [str(l) for l in value_counts.index.tolist()],
                    'values': value_counts.values.tolist(),
                    'columnName': column
                }

    return render_template("stats.html",
                           chart_data=chart_data,
                           list_mois=list_mois,
                           mois=mois,
                           columns=df.columns.tolist(),
                           column_name=column_name)

@app.route("/visibility")
@login_required
def visibility_page():
    """Admin UI to configure visibility rules."""
    AllCols = backend_api_get_columns()
    AllCols = AllCols['all_columns']
    ColsNames = list(map(lambda col : col['column_name'], AllCols))
    print("names", ColsNames)
    allColumns = ColsNames
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    # make sure all columns are in here first?
    clinic_id = session.get('clinic_id')
    cur.execute("SELECT role, columns FROM column_visibility WHERE clinic_id = %s;", (clinic_id,))
    rows = cur.fetchall()
    return render_template("visibility.html", roles=rows, allColumns=ColsNames)

@app.route("/get_visibility/<role>")
@login_required
def get_visibility(role):
    """API endpoint for frontend JS to fetch visible columns for a role."""
    clinic_id = session.get('clinic_id')
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT columns FROM column_visibility WHERE role=%s AND clinic_id=%s;", (role, clinic_id))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify(row["columns"] if row else [])


def get_visibility_backend(role):
    """Backend helper to fetch visible columns for a role."""
    clinic_id = session.get('clinic_id')
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT columns FROM column_visibility WHERE role=%s AND clinic_id=%s;", (role, clinic_id))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["columns"] if row else []

@app.route("/update_visibility", methods=["POST"])
@login_required
def update_visibility():
    """API endpoint for admin UI to update rules."""
    data = request.json
    role = data.get("role")
    new_columns = data.get("columns", [])
    print("here")
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    clinic_id = session.get('clinic_id')
    cur.execute(
        "UPDATE column_visibility SET columns=%s WHERE role=%s AND clinic_id=%s;",
        (json.dumps(new_columns), role, clinic_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success", "columns": new_columns})




# New routes for dynamic column management
@app.route('/manage_columns')
@login_required
def manage_columns():
    """Show column management interface"""
    columns = get_all_columns()
    return render_template('manage_columns.html', columns=columns)

# SAME THING AS API BUT THE OUTPUT IS DIFFERENT SO DONT TOUCH THIS LOL
def backend_api_get_columns():
    """API endpoint to get column configuration"""
    visible_columns = get_visible_columns()
    all_columns = get_all_columns()
    
    # Convert RealDictRow to regular dictionaries for JSON serialization
    visible_columns_list = [dict(row) for row in visible_columns]
    all_columns_list = [dict(row) for row in all_columns]
    
    return {
        'visible_columns': visible_columns_list,
        'all_columns': all_columns_list
    }

@app.route('/api/columns', methods=['GET'])
@login_required
def api_get_columns():
    """API endpoint to get column configuration"""
    visible_columns = get_visible_columns()
    all_columns = get_all_columns()
    
    # Convert RealDictRow to regular dictionaries for JSON serialization
    visible_columns_list = [dict(row) for row in visible_columns]
    all_columns_list = [dict(row) for row in all_columns]
    
    return jsonify({
        'visible_columns': visible_columns_list,
        'all_columns': all_columns_list
    })

@app.route('/api/add_column', methods=['POST'])
@login_required
def api_add_column():
    """API endpoint to add a new column"""
    data = request.get_json()
    
    if not data or not data.get('column_name') or not data.get('display_name'):
        return jsonify({'status': 'error', 'message': 'Column name and display name are required'}), 400
    
    column_name = data['column_name'].strip().lower().replace(' ', '_')
    display_name = data['display_name'].strip()
    data_type = data.get('data_type', 'TEXT')
    
    # Validate column name (alphanumeric and underscore only)
    import re
    if not re.match('^[a-zA-Z_][a-zA-Z0-9_]*$', column_name):
        return jsonify({'status': 'error', 'message': 'Invalid column name. Use only letters, numbers, and underscores.'}), 400
    
    # Check if column already exists
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    clinic_id = session.get('clinic_id')
    cur.execute('SELECT COUNT(*) FROM patient_columns_meta WHERE column_name = %s AND clinic_id = %s', (column_name, clinic_id))
    result = cur.fetchone()
    count = result.get('count', 0) if hasattr(result, 'get') else result[0]
    if count > 0:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Column already exists'}), 400
    
    # Add to database table
    if not add_column_to_patients(column_name, data_type):
        return jsonify({'status': 'error', 'message': 'Failed to add column to database'}), 500
    
    # Add to metadata
    cur.execute('SELECT MAX(display_order) as max_order FROM patient_columns_meta WHERE clinic_id = %s', (clinic_id,))
    result = cur.fetchone()
    max_order = result.get('max_order', 0) if hasattr(result, 'get') else (result[0] or 0)
    if max_order is None:
        max_order = 0
    
    cur.execute('''
        INSERT INTO patient_columns_meta
        (column_name, display_name, data_type, is_visible, is_required, display_order, clinic_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (column_name, display_name, data_type, True, False, max_order + 1, clinic_id))

    # Add to the column visibility table for this clinic
    cur.execute("""
        UPDATE column_visibility
        SET columns = columns::jsonb || %s::jsonb
        WHERE role = %s AND clinic_id = %s;
        """,
        (f'["{column_name}"]', 'medecins', clinic_id)
    )

    conn.commit()
    conn.close()
    
    log_file(session.get('user_type'), 'Column Added', f"Added column: {display_name} ({column_name})")
    
    return jsonify({'status': 'success', 'message': 'Column added successfully'})

@app.route('/api/toggle_column/<column_name>', methods=['POST'])
@login_required
def api_toggle_column(column_name):
    """API endpoint to toggle column visibility"""
    data = request.get_json()
    is_visible = data.get('is_visible', True)
    
    # Don't allow hiding essential columns
    essential_columns = ['id', 'name']
    if column_name in essential_columns and not is_visible:
        return jsonify({'status': 'error', 'message': 'Cannot hide essential columns'}), 400
    
    update_column_visibility(column_name, is_visible)
    
    action = 'shown' if is_visible else 'hidden'
    log_file(session.get('user_type'), 'Column Visibility Changed', f"Column {column_name} {action}")
    
    return jsonify({'status': 'success', 'message': f'Column visibility updated'})

@app.route('/api/remove_column/<column_name>', methods=['DELETE'])
@login_required
def api_remove_column(column_name):
    """API endpoint to remove a column"""
    # Don't allow removal of essential columns
    essential_columns = ['id', 'name', 'created_at']
    if column_name in essential_columns:
        return jsonify({'status': 'error', 'message': 'Cannot remove essential columns'}), 400
    
    # Remove from database table
    if not remove_column_from_patients(column_name):
        return jsonify({'status': 'error', 'message': 'Failed to remove column from database'}), 500
    
    # Remove from metadata
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    clinic_id = session.get('clinic_id')
    cur.execute('DELETE FROM patient_columns_meta WHERE column_name = %s AND clinic_id = %s', (column_name, clinic_id))

    # Remove from visibility for this clinic
    cur.execute("SELECT role, columns FROM column_visibility WHERE clinic_id = %s;", (clinic_id,))
    rows = cur.fetchall()
    # you just added this now you need to get the list for a role specific, remove the old column and then introducte that in the db
    roles_dict = {row['role']: row['columns'] for row in rows}

    # for each role remove the column that we dont want
    for key in roles_dict.keys():
        print(key, column_name, roles_dict[key])
        if column_name in roles_dict[key]:
            val = roles_dict[key]
            newval = [value for value in val if value != column_name]

            roles_dict[key] = newval
            print('new val', roles_dict[key], newval)
            try:
                cur.execute("UPDATE column_visibility SET columns = %s WHERE role = %s AND clinic_id = %s", (json.dumps(roles_dict[key]), key, clinic_id))
                print(f"UPDATED row {key}")
                print(roles_dict)
            except Exception as e:
                print(f"Error processing row {key} : {e}")


    conn.commit()
    conn.close()
    
    log_file(session.get('user_type'), 'Column Removed', f"Removed column: {column_name}")
    
    return jsonify({'status': 'success', 'message': 'Column removed successfully'})