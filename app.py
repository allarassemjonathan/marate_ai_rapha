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
    with get_db_connection() as conn:
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
            conn.commit()



init_db()
# on_startup()

print('hello')
app.secret_key = os.environ.get('FLASK_SECRET')

# Simple credential storage (in production, use a database)
CREDENTIALS = {
    'medecins': os.environ.get('medecins'),
    'infirmiers': os.environ.get('infirmiers'), 
    'receptionistes': os.environ.get('receptionistes')
}

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
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
    init_db()
    # restore the db in drive
    if session.get('logged_in'):
        user_type = session.get('user_type')
        print(user_type)
        return render_template('index.html', user_type = user_type)
    return redirect(url_for('login'))

@app.route('/search')
@login_required
def search():
    q = request.args.get('q', '')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM patients WHERE name ILIKE %s OR adresse ILIKE %s",
        tuple(f'%{q}%' for _ in range(2))
    )
    results = cur.fetchall()
    conn.close()
    return jsonify(results)

# @app.rout('/stat')
# @login_required
# def stat():
#     conn = get_db_connection()
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM patients")
#     results = cur.fetchall()
    
from datetime import date
@app.route('/add', methods=['POST'])
@login_required
def add():
    data = request.get_json() or {}
    
    # List of known date fields in the table
    date_fields = {'name', 'adresse', 'date_of_birth'} #'taille', 'tension_arterielle', 'temperature', 'hypothese_de_diagnostique', 'bilan', 'resultat_bilan', 'signature', 'renseignements_clinique', 'ordonnance', 'created_at'}

    # Replace empty strings with None for date fields
    cleaned_data = {}
    for k, v in data.items():
        if k in date_fields and v == '':
            cleaned_data[k] = None
        else:
            cleaned_data[k] = v

    data = cleaned_data
    if not data.get('name'):
        return jsonify({'status': 'error', 'message': 'Name is required'}), 400

    try:
        data['created_at'] = date.today().isoformat()

        # Fields that should be treated as floats in the DB
        float_fields = {'age', 'poids', 'taille', 'tension_arterielle', 'temperature'}

        for field in float_fields:
            if field in data:
                if data[field] == '':
                    data[field] = None
                else:
                    try:
                        data[field] = float(data[field])
                    except ValueError:
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

        return jsonify({'status': 'success'})

    except Exception as e:
        print(e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/delete/<int:rowid>', methods=['DELETE'])
@login_required
def delete(rowid):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM patients WHERE id = %s', (rowid,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'deleted'})

@app.route('/patient/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, * FROM patients WHERE id = %s', (patient_id,))
    patient = cur.fetchone()

    cur.execute('SELECT * FROM visits WHERE patient_id = %s', (patient_id,))
    visits = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    conn.close()

    return render_template('patient.html', patient=dict(zip(columns, patient)) if patient else None, visits=visits) if patient else ("Patient not found", 404)

@app.route('/get_patient/<int:patient_id>')
@login_required
def get_patient(patient_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, * FROM patients WHERE id = %s', (patient_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return jsonify(row)
    return jsonify({'status': 'error', 'message': 'Patient not found'}), 404

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

    if data.get('temperature') != '':
        email_reception(data['name'], '', 'Cher medecin, vous avez un nouveau malade. Certaines informations ont ete modifie et il semble que votre malade est prêt.', None, acteur_med)

    return jsonify({'status': 'success'})


@app.route('/logout')
@login_required
def logout():
    session.clear()  # Clears all session data
    return redirect(url_for('login'))  # Redirects to login page

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('index', user_type = session.get('user_type')))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check credentials
        if username in CREDENTIALS and CREDENTIALS[username] == password:
            session['user_type'] = username
            session['logged_in'] = True
            return redirect(url_for('index', user_type = username))
        else:
            flash('Invalid credentials')
    
    return render_template('login.html')