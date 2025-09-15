from collections import defaultdict
from flask import Flask, render_template, request, jsonify, send_file, session, flash, redirect, url_for
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
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
app = Flask(__name__)


# If modifying these scopes, delete the token.json
SCOPES = ['https://www.googleapis.com/auth/drive.file']


def clean_float(value):
    return float(value) if value.strip() != "" else None

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
def init_db():
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    adresse TEXT,
                    age INTEGER,
                    date_of_birth DATE, 
                    poids REAL,
                    taille REAL,
                    tension_arterielle REAL,
                    temperature REAL,
                    hypothese_de_diagnostique TEXT,
                    bilan TEXT, 
                    resultat_bilan TEXT,
                    signature TEXT,
                    renseignements_clinique TEXT,
                    ordonnance TEXT,
                    created_at DATE
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS visits (
                    id SERIAL PRIMARY KEY,
                    patient_id INTEGER REFERENCES patients(id),
                    visit_date DATE,
                    notes TEXT
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS action_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    user_type TEXT,
                    action TEXT NOT NULL,
                    details TEXT
                )
            ''')
            # Create the column metadata table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS patient_columns_meta (
                    id SERIAL PRIMARY KEY,
                    column_name TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    is_visible BOOLEAN DEFAULT TRUE,
                    is_required BOOLEAN DEFAULT FALSE,
                    display_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            # Check if metadata exists, if not populate with existing columns
            cur.execute("SELECT COUNT(*) FROM patient_columns_meta")
            result = cur.fetchone()
            
            if result is None:
                count = 0
            else:
                # Handle both tuple and RealDictRow formats
                if hasattr(result, 'get'):
                    count = result.get('count', 0)
                else:
                    count = result[0]
            
            if count == 0:
                # Insert default column metadata
                default_columns = [
                    ('id', 'ID', 'SERIAL', True, True, 1),
                    ('name', 'Nom', 'TEXT', True, True, 2),
                    ('adresse', 'Adresse', 'TEXT', True, False, 3),
                    ('age', 'Âge', 'INTEGER', True, False, 4),
                    ('date_of_birth', 'Date de naissance', 'DATE', True, False, 5),
                    ('poids', 'Poids', 'REAL', True, False, 6),
                    ('taille', 'Taille', 'REAL', True, False, 7),
                    ('tension_arterielle', 'Tension artérielle', 'REAL', True, False, 8),
                    ('temperature', 'Température', 'REAL', True, False, 9),
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
                        (column_name, display_name, data_type, is_visible, is_required, display_order)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (col_name, display_name, data_type, is_visible, is_required, order))
            
            conn.commit()

# Column management utility functions
def get_visible_columns():
    """Get list of visible columns in display order"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT column_name, display_name, data_type 
        FROM patient_columns_meta 
        WHERE is_visible = TRUE 
        ORDER BY display_order
    ''')
    columns = cur.fetchall()
    conn.close()
    return columns

def get_all_columns():
    """Get all columns with their metadata"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT column_name, display_name, data_type, is_visible, is_required, display_order
        FROM patient_columns_meta 
        ORDER BY display_order
    ''')
    columns = cur.fetchall()
    conn.close()
    return columns

def add_column_to_patients(column_name, data_type):
    """Add a new column to the patients table"""
    conn = get_db_connection()
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
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        UPDATE patient_columns_meta 
        SET is_visible = %s 
        WHERE column_name = %s
    ''', (is_visible, column_name))
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

init_db()
# on_startup()

print('hello')
app.secret_key = os.environ.get('FLASK_SECRET')
Special_user = ''
# Simple credential storage (in production, use a database)
CREDENTIALS = {
    'medecins': os.environ.get('medecins'),
    'infirmiers': os.environ.get('infirmiers'), 
    'receptionistes': os.environ.get('receptionistes'),
    'Dr_Toralta_G_.Josephine':os.environ.get('Dr_Toralta_G_.Josephine'),
    'Dr_Djaury_Dadji_-A':os.environ.get('Dr_Djaury_Dadji_-A'),
    'Dr_Ndortolnan_Azer':os.environ.get('Dr_Ndortolnan_Azer'), 
    'Dr_Doumgo_Monna_Doni_Nelson':os.environ.get('Dr_Doumgo_Monna_Doni_Nelson'), 
    'Dr_Ngetigal_Hyacinte':os.environ.get('Dr_Ngetigal_Hyacinte'), 
    'Dr_Ousmane_Hamane_Gadji':os.environ.get('Dr_Ousmane_Hamane_Gadji'), 
    'Dr_Toralta_Emmanuelle_Mantar':os.environ.get('Dr_Toralta_Emmanuelle_Mantar'), 
    'Dr_Madjibeye_Mirielle':os.environ.get('Dr_Madjibeye_Mirielle'), 
    'Dr_Robnodji_Adoucie':os.environ.get('Dr_Robnodji_Adoucie'), 
    'Dr_Ndoubane_Bonheur': os.environ.get('Dr_Ndoubane_Bonheur')
}

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If either logged_in or username missing → go to login
        if not session.get('logged_in') or not session.get('username'):
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
    def header(self):
        # Add logo if possible
        try:
            logo_rapha = "https://allarassemjonathan.github.io/rapha_logo.png"
            logo_url = "https://allarassemjonathan.github.io/marate_white.png"
            response = requests.get(logo_url, timeout=10)
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                    tmp_file.write(response.content)
                    tmp_file.flush()
                    self.image(tmp_file.name, 10, 8, 40)
            
            other_res= requests.get(logo_rapha, timeout=10)
            if other_res.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                    tmp_file.write(other_res.content)
                    tmp_file.flush()
                    self.image(tmp_file.name, 160, 8, 40)

        except Exception as e:
            print(f"Could not load logo: {e}")

        self.set_font('Arial', 'B', 16)
        self.set_text_color(6, 182, 212)
        self.cell(0, 10, 'Devis Cabinet RAPHA', border=False, ln=1, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def add_patient_info(self, patient):
        self.set_font('Arial', '', 11)
        self.set_text_color(0)

        self.cell(100, 10, f"Nom: {patient['name']}", ln=0)
        self.cell(90, 10, "Cabinet dentaire la renaissance", ln=1)

        self.cell(100, 10, f"Adresse: {patient['adresse'] or 'N/A'}", ln=0)
        self.cell(90, 10, "Kantara Sacko, Rue 22, Medina Dakar", ln=1)

        self.cell(100, 10, f"Date de naissance: {patient['date_of_birth'] or 'N/A'}", ln=0)
        self.cell(90, 10, "cablarenaissance@gmail.com", ln=1)

        self.cell(100, 10, f"Date de facture: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=0)
        self.cell(90, 10, "(+221) 78 635 95 65", ln=1)
        self.ln(5)

    def add_invoice_header(self, meta):
        dic =  { "January": "Janvier",
            "February": "Février",
            "March": "Mars",
            "April": "Avril",
            "May": "Mai",
            "June": "Juin",
            "July": "Juillet",
            "August": "Août",
            "Septembe": "Septembre",
            "October": "Octobre",
            "November": "Novembre",
            "December": "Décembre"}
        assurance = meta.get('assurance', '')
        envoye_a = meta.get('envoye_a', '')
        now = datetime.now()
        mois_annee = now.strftime('%B %Y').capitalize()
        month = mois_annee.split(' ')[0]
        print(month)
        mois_annee = mois_annee.replace(month, dic.get(month))
        
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0)
        self.cell(0, 10, f"Société d'assurance : {assurance}", ln=1, align='C')
        self.cell(0, 10, f"Facture du mois de {mois_annee}", ln=1, align='C')
        if envoye_a:
            self.cell(0, 10, f"{envoye_a}", ln=1, align='C')
        self.cell(0, 10, "doit au cabinet Rapha", ln=1, align='C')
        self.ln(5)

        # Then the usual patient metadata below
        self.set_font('Arial', '', 11)
        self.set_text_color(0)
        self.cell(95, 10, f"Nom: {meta.get('nom', '')}", ln=0)
        self.cell(95, 10, f"N° Police: {meta.get('police', '')}", ln=1)

        self.cell(95, 10, f"Prénom: {meta.get('prenom', '')}", ln=0)

        self.cell(95, 10, f"Date: {now.strftime('%d/%m/%Y')}", ln=1)
        self.ln(5)

    def add_invoice_sections(self, sections, pourcentage_patient):
        total_net = 0
        self.set_font('Arial', 'B', 12)

        for section in sections:
            self.set_fill_color(6, 182, 212)
            self.set_text_color(255)
            self.cell(0, 10, section.get('titre', 'Section'), 1, 1, 'C', 1)

            headers = ['Libellé', 'Quantité', 'Montant unitaire', f'% Assurance', 'Net à payer']
            col_widths = [50, 30, 35, 25, 45]

            self.set_font('Arial', 'B', 11)
            for i, header in enumerate(headers):
                print("Rendering table headers for section:", section.get('titre', 'Section'))
                self.cell(col_widths[i], 10, header, 1, 0, 'C', True)
            self.ln()

            self.set_font('Arial', '', 10)
            self.set_text_color(0)

            sous_total = 0

            for article in section.get('articles', []):
                qte = float(article.get('quantite', 1))
                brut = float(article.get('montant', 0))
                net = round(brut * qte * pourcentage_patient / 100)
                sous_total += net
                total_net += net

                row = [
                    article.get('libelle', ''),
                    str(int(qte)),
                    f"{int(brut)} Fcfa",
                    f"{int(100 - pourcentage_patient)}%",
                    f"{int(net)} Fcfa"
                ]
                for i, datum in enumerate(row):
                    self.cell(col_widths[i], 10, datum, 1)
                self.ln()

            # Add section subtotal
            self.set_font('Arial', 'B', 11)
            self.set_text_color(6, 182, 212)
            self.cell(sum(col_widths[:-1]), 10, "Sous-total de la section", 1, 0, 'R')
            self.cell(col_widths[-1], 10, f"{int(sous_total)} Fcfa", 1, 1, 'C')

            self.ln(3)

        # Final total
        self.set_font('Arial', 'B', 12)
        self.set_text_color(220, 20, 60)
        self.cell(0, 10, f"MONTANT À PAYER PAR LE PATIENT: {int(total_net)} Fcfa", ln=1, align='C')

    def add_invoice_table(self, items):
        self.set_font('Arial', 'B', 11)
        self.set_fill_color(6, 182, 212)
        self.set_text_color(255)
        headers = ['Article', 'Quantité', 'Prix Unitaire', 'Prix Total', 'Date']
        col_widths = [40, 25, 35, 35, 40]

        for i, header in enumerate(headers):
            print("Rendering table headers for section:", section.get('titre', 'Section'))
            self.cell(col_widths[i], 10, header, 1, 0, 'C', 1, True)
        self.ln()

        self.set_font('Arial', '', 10)
        self.set_text_color(0)

        total_amount = 0
        for item in items:
            quantity = int(str(item['quantity']).replace(' ', ''))
            price = int(str(item['price']).replace(' ', ''))
            total_price = quantity * price
            total_amount += total_price

            row = [
                str(item['name']),
                str(quantity),
                f"{price} Fcfa",
                f"{total_price} Fcfa",
                datetime.now().strftime('%d/%m/%Y')
            ]
            for i, datum in enumerate(row):
                self.cell(col_widths[i], 10, datum, 1)
            self.ln()

        # Total row
        self.set_font('Arial', 'B', 11)
        self.cell(col_widths[0] + col_widths[1] + col_widths[2], 10, 'TOTAL:', 1)
        self.cell(col_widths[3], 10, f"{total_amount} Fcfa", 1)
        self.cell(col_widths[4], 10, '', 1)
        self.ln(10)

        # Insurance breakdown
        insurance_amount = int(total_amount * 0.80)
        patient_amount = total_amount - insurance_amount

        self.set_font('Arial', '', 11)
        self.cell(60, 10, f"Part Assureur (80%): {insurance_amount} Fcfa", ln=1)
        self.cell(60, 10, f"Part Patient (20%): {patient_amount} Fcfa", ln=1)

        self.ln(5)
        self.set_font('Arial', 'B', 12)
        self.set_text_color(220, 20, 60)
        self.cell(0, 10, f"MONTANT À PAYER PAR LE PATIENT: {patient_amount} Fcfa", ln=1, align='C')


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
        pdf.add_page()
        pdf.add_invoice_header(meta)
        pdf.add_invoice_sections(sections, pourcentage_patient)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf.output(tmp_file.name)
            tmp_file.seek(0)

            filename = f"facture_{meta['nom']}_{meta['prenom']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            log_file(
                session.get('user_type'),
                'Facture généré',
                f"Facture généré pour le patient {meta.get('nom')} {meta.get('prenom')}"
            )
            return send_file(
                tmp_file.name,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )

    except Exception as e:
        print(f"Error generating invoice: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@app.route('/')
@login_required
def index():
    init_db()  # Restore DB in drive, etc.

    user_type = session.get('user_type')

    if user_type in ['receptionistes', 'infirmiers']:
        username = user_type[:-1]
    else:
        username = session['username'].replace('_', ' ')

    # Get visible columns for dynamic display
    visible_columns = get_visible_columns()

    return render_template('index.html', 
                         user_type=user_type, 
                         username=username,
                         visible_columns=visible_columns)


@app.route('/search')
@login_required
def search():
    q = request.args.get('q', '')
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get visible columns for dynamic query
    visible_columns = get_visible_columns()
    column_names = [col['column_name'] for col in visible_columns]
    
    if not column_names:
        return jsonify([])
    
    # Build dynamic SELECT query
    select_columns = ', '.join(column_names)
    cur.execute(
        f"SELECT {select_columns} FROM patients WHERE name ILIKE %s OR adresse ILIKE %s",
        tuple(f'%{q}%' for _ in range(2))
    )
    results = cur.fetchall()
    conn.close()
    
    # Convert RealDictRow to regular dict for JSON serialization
    formatted_results = []
    for row in results:
        formatted_results.append(dict(row))
    
    return jsonify(formatted_results)

@app.route('/distribution')
def show_distribution():
    conn = get_db_connection()
    cur = conn.cursor()

    columns = ['adresse', 'sexe', 'groupe_sanguin']
    all_values = defaultdict(lambda: defaultdict(int))

    for col in columns:
        cur.execute(f"SELECT {col} FROM patients")
        rows = cur.fetchall()
        for (val,) in rows:
            if val:
                all_values[col][val] += 1

    cur.close()
    conn.close()

    return render_template("distribution.html", distributions=all_values)

from datetime import datetime, timezone, timedelta # chad timezone attempt
from datetime import date
@app.route('/add', methods=['POST'])
@login_required
def add():
    data = request.get_json() or {}
    print(data)
    # List of known date fields in the table
    date_fields = {'name', 'adresse', 'date_of_birth', 'tension_arterielle'} #'taille', 'tension_arterielle', 'temperature', 'hypothese_de_diagnostique', 'bilan', 'resultat_bilan', 'signature', 'renseignements_clinique', 'ordonnance', 'created_at'}

    # Replace empty strings with None for date fields
    cleaned_data = {}
    for k, v in data.items():
        if k in date_fields and v == '':
            cleaned_data[k] = None
        else:
            cleaned_data[k] = v

    data = cleaned_data
    if not data.get('name'):
        print('issue is here 1 ')
        return jsonify({'status': 'error', 'message': 'Name is required'}), 400

    try:
        gmt_plus1 = timezone(timedelta(hours=1))
        data['created_at'] = datetime.now(gmt_plus1)

        # Fields that should be treated as floats in the DB
        float_fields = {'age', 'poids', 'taille', 'temperature'}

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
                        print('issue is here 2 ')
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
        # Use parameterized query
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ', '.join(['%s'] * len(values))
        print(placeholders, values)
        col_names = ', '.join(columns)

        query = f'INSERT INTO patients ({col_names}) VALUES ({placeholders})'

        conn = get_db_connection()
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
    cur = conn.cursor()
    cur.execute('SELECT * FROM patients WHERE id = %s', (rowid, ))
    row = cur.fetchall()
    cur.execute('DELETE FROM patients WHERE id = %s', (rowid,))
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
    cur = conn.cursor()
    cur.execute('SELECT * FROM patients WHERE id = %s', (patient_id,))
    patients = cur.fetchall()

    row_as_dicts = [dict(row) for row in patients]
    
    print(patients)
    print(row_as_dicts[0])

    name = row_as_dicts[0]['name']
    print('name', name)
    cur.execute('SELECT * FROM patients WHERE name = %s', (name,))
    visits = cur.fetchall()
    print(len(visits))

    row_as_visits = [dict(row) for row in visits]
    return render_template('patient.html', visits = row_as_visits, patient=row_as_dicts[0])

@app.route('/get_patient/<int:patient_id>')
@login_required
def get_patient(patient_id):
    user_type = session.get('user_type')
    log_file(user_type, 'Patient sélectionné', f"Patient avec ID {patient_id} selectionné.")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM patients WHERE id = %s', (patient_id,))
    row = cur.fetchone()
    print(row)

    row =dict(row)
    print(row)
    conn.close()
    print(session['username'])

    if user_type=='infirmiers' or user_type == 'receptionistes':
        return jsonify(row)
    if row['signature'] is None:
        return jsonify(row)
    if session['username'] == 'Dr_Toralta_G_.Josephine':
        print('ot here?')
        return jsonify(row)
    if row and row['signature'] and row['signature'] == session['username'].replace('_', ' '):
        return jsonify(row)
    else:
        print('ieah')
        return jsonify({'status': 'error', 'message': f"Seul le {row['signature']} a le droit de modifier ce patient."})

# we will use later .. 

@app.route('/stat')
@login_required
def stat():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('select COUNT(*) from patients')
    count = dict(cur.fetchall()[0])['count']
    cur.execute('select AVG(age) from patients')
    avg_age = dict(cur.fetchall()[0])['avg']
    cur.execute('select AVG(taille) from patients')
    avg_height = dict(cur.fetchall()[0])['avg']
    cur.execute('select AVG(poids) from patients')
    avg_weight = dict(cur.fetchall()[0])['avg']
    return f"{count} patients cette annee -- {round(avg_age)} ans en moyenne -- {round(avg_height)} cm en moyenne -- {round(avg_weight)} kg en moyenne "

@app.route('/update/<int:patient_id>', methods=['PUT'])
@login_required
def update_patient(patient_id):
    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'status': 'error', 'message': 'Name is required'}), 400

    # List of known date fields in the table
    date_fields = {'name', 'adresse', 'age', 'date_of_birth', 'poids', 'taille', 'tension_arterielle', 'temperature', 'hypothese_de_diagnostique', 'bilan', 'resultat_bilan', 'signature', 'renseignements_clinique', 'ordonnance', 'created_at'}


    # Replace empty strings with None for date fields
    cleaned_data = {}
    for k, v in data.items():
        if k in date_fields and v == '':
            cleaned_data[k] = None
        else:
            cleaned_data[k] = v

    set_clause = ", ".join([f"{k} = %s" for k in cleaned_data.keys()])
    values = list(cleaned_data.values())
    values.append(patient_id)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f'UPDATE patients SET {set_clause} WHERE id = %s', values)
    conn.commit()
    conn.close()

    log_file(
        session.get('user_type'),
        'modification patient',
        f"Patient avec ID {patient_id} a été modifié"
    )

    if data.get('temperature') != '':
        email_reception(data['name'], '', 'Cher medecin, vous avez un nouveau malade. Certaines informations ont été modifié et il semble que votre malade est prêt.', None, acteur_med)

    return jsonify({'status': 'success'})


@app.route('/logout')
@login_required
def logout():
    user_type = session.get('user_type')
    log_file(user_type, 'logout', f"L'utilisateur '{user_type}' s'est déconnecté")
    session.clear()  # Clears all session data
    return redirect(url_for('login'))  # Redirects to login page

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, go to index
    if session.get('logged_in') and session.get('username') and session.get('user_type'):
        return redirect(url_for('index', user_type=session.get('user_type')))

    if request.method == 'POST':
        username_input = request.form['username'].replace(' ', '_')
        password = request.form['password']

        # Check credentials
        if username_input in CREDENTIALS and CREDENTIALS[username_input] == password:
            physicians = {
                'Dr_Toralta_G_.Josephine', 'Dr_Djaury_Dadji_-A', 'Dr_Ndortolnan_Azer',
                'Dr_Doumgo_Monna_Doni_Nelson', 'Dr_Ngetigal_Hyacinte', 'Dr_Ousmane_Hamane_Gadji',
                'Dr_Toralta_Emmanuelle_Mantar', 'Dr_Madjibeye_Mirielle',
                'Dr_Robnodji_Adoucie', 'Dr_Ndoubane_Bonheur'
            }

            # Always set both username & user_type
            if username_input in physicians:
                session['username'] = username_input
                session['user_type'] = 'medecins'
            else:
                session['username'] = username_input  # ✅ Added so it's never missing
                session['user_type'] = username_input

            session['logged_in'] = True
            log_file(username_input, 'login', f"L'utilisateur '{username_input}' s'est connecté avec succès")
            return redirect(url_for('index', user_type=session['user_type']))
        else:
            flash('Rôle et/ou mot de passe incorrects.')
            log_file(username_input, 'La connexion a échoué', "Failed login attempt")

    return render_template('login.html')


from io import StringIO
from datetime import date, timedelta

def generate_daily_report(date_of_report=None):
    if date_of_report is None:
        date_of_report = date.today()

    next_day = date_of_report + timedelta(days=1)
    conn = get_db_connection()
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
def send_daily_report_email():
    today = date.today()
    # report = generate_daily_report(today)
    report = '/n'.join(open('daily_log.txt', 'r', encoding='latin-1').readlines())

    # Compose email
    subject = f"Daily Action Report for {today.strftime('%Y-%m-%d')}"
    msg = MIMEMultipart()
    msg['From'] = your_email
    msg['To'] =  "Josephinetoralta@gmail.com"
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
        Le rapport journalier des connections au logiciel a été envoyée a l'email Josephinetoralta@gmail.com!
        <br>
        <a href="/">Retour menu <a/>
        """
        
    except Exception as e:
        return f"Failed to send daily report email: {e}"

# New routes for dynamic column management
@app.route('/manage_columns')
@login_required
def manage_columns():
    """Show column management interface"""
    columns = get_all_columns()
    return render_template('manage_columns.html', columns=columns)

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
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM patient_columns_meta WHERE column_name = %s', (column_name,))
    result = cur.fetchone()
    count = result.get('count', 0) if hasattr(result, 'get') else result[0]
    if count > 0:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Column already exists'}), 400
    
    # Add to database table
    if not add_column_to_patients(column_name, data_type):
        return jsonify({'status': 'error', 'message': 'Failed to add column to database'}), 500
    
    # Add to metadata
    cur.execute('SELECT MAX(display_order) as max_order FROM patient_columns_meta')
    result = cur.fetchone()
    max_order = result.get('max_order', 0) if hasattr(result, 'get') else (result[0] or 0)
    if max_order is None:
        max_order = 0
    
    cur.execute('''
        INSERT INTO patient_columns_meta 
        (column_name, display_name, data_type, is_visible, is_required, display_order)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (column_name, display_name, data_type, True, False, max_order + 1))
    
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
    cur = conn.cursor()
    cur.execute('DELETE FROM patient_columns_meta WHERE column_name = %s', (column_name,))
    conn.commit()
    conn.close()
    
    log_file(session.get('user_type'), 'Column Removed', f"Removed column: {column_name}")
    
    return jsonify({'status': 'success', 'message': 'Column removed successfully'})