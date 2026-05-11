# Cabinet RAPHA - Architecture UML

## Use Case Diagram

```mermaid
@startuml

actor "Medecin\n(Docteur)" as doc
actor "Infirmier\n(Nurse)" as nurse
actor "Receptioniste" as recep
actor "Manager\n(Admin)" as admin

rectangle "Cabinet RAPHA - Systeme de Gestion des Patients" {

  ' === Authentication ===
  package "Authentification" {
    usecase "Se connecter\n(Login)" as UC_LOGIN
    usecase "Verification SMS 2FA\n(Twilio)" as UC_2FA
    usecase "Se deconnecter" as UC_LOGOUT
  }

  ' === Patient Management ===
  package "Gestion des Patients" {
    usecase "Consulter la liste\ndes patients" as UC_LIST
    usecase "Rechercher un patient" as UC_SEARCH
    usecase "Ajouter un patient" as UC_ADD
    usecase "Modifier un patient" as UC_UPDATE
    usecase "Supprimer un patient" as UC_DELETE
    usecase "Voir fiche patient" as UC_VIEW
  }

  ' === Hospitalization ===
  package "Hospitalisation" {
    usecase "Creer une hospitalisation" as UC_HOSP_ADD
    usecase "Modifier une hospitalisation" as UC_HOSP_EDIT
    usecase "Gerer les traitements" as UC_TREAT
    usecase "Supprimer une hospitalisation" as UC_HOSP_DEL
  }

  ' === Billing ===
  package "Facturation" {
    usecase "Generer une facture PDF" as UC_INVOICE
    usecase "Saisir un paiement (IPM)" as UC_IPM
  }

  ' === Analytics ===
  package "Statistiques & Rapports" {
    usecase "Tableau de bord" as UC_DASH
    usecase "Revenu journalier" as UC_REV_J
    usecase "Revenu mensuel" as UC_REV_M
    usecase "Frequentation patients" as UC_FREQ
    usecase "Repartition par quartier" as UC_QUART
    usecase "Evolution des patients" as UC_EVOL
    usecase "Rapport email\navec graphiques" as UC_REPORT
  }

  ' === Administration ===
  package "Administration" {
    usecase "Gerer les colonnes\ndynamiques" as UC_COLS
    usecase "Configurer la visibilite\npar role" as UC_VISI
  }
}

' --- Relationships ---

' All actors authenticate
doc --> UC_LOGIN
nurse --> UC_LOGIN
recep --> UC_LOGIN
admin --> UC_LOGIN
UC_LOGIN ..> UC_2FA : <<include>>

doc --> UC_LOGOUT
nurse --> UC_LOGOUT
recep --> UC_LOGOUT

' Patient management
doc --> UC_LIST
nurse --> UC_LIST
recep --> UC_LIST

doc --> UC_SEARCH
nurse --> UC_SEARCH
recep --> UC_SEARCH

doc --> UC_ADD
nurse --> UC_ADD
recep --> UC_ADD

doc --> UC_UPDATE
nurse --> UC_UPDATE

doc --> UC_DELETE

doc --> UC_VIEW
nurse --> UC_VIEW
recep --> UC_VIEW

' Hospitalization
doc --> UC_HOSP_ADD
doc --> UC_HOSP_EDIT
doc --> UC_TREAT
doc --> UC_HOSP_DEL

' Billing
doc --> UC_INVOICE
recep --> UC_IPM

' Analytics
doc --> UC_DASH
admin --> UC_DASH
doc --> UC_REV_J
doc --> UC_REV_M
doc --> UC_FREQ
doc --> UC_QUART
doc --> UC_EVOL
doc --> UC_REPORT

' Administration
admin --> UC_COLS
admin --> UC_VISI

' Notes
note right of doc
  Les medecins ne voient
  que leurs propres patients
  (doctor ownership)
end note

note right of admin
  Le manager a acces
  a tous les patients
  et toutes les fonctions
end note

@enduml
```

## Component Diagram

```mermaid
@startuml

package "Frontend (Navigateur)" {
  [Templates Jinja2\n(HTML/Tailwind CSS)] as UI
  [search.js\n(Vanilla JS)] as JS
}

package "Backend (Flask - app.py)" {

  package "Authentification & Securite" {
    [login_required\n(decorator)] as AUTH
    [Argon2 + Pepper\n(hashing)] as HASH
    [Twilio SMS 2FA] as SMS
  }

  package "Routes & Logique Metier" {
    [Gestion Patients\nCRUD] as PATIENTS
    [Hospitalisation\n& Traitements] as HOSP
    [Recherche\n& Filtrage] as SEARCH
    [Statistiques\n& Dashboard] as STATS
  }

  package "Services" {
    [InvoicePDF\n(fpdf2)] as PDF
    [Email SMTP\n(Gmail)] as EMAIL
    [Matplotlib\n(Graphiques)] as GRAPH
    [Logging\n(daily_log.txt)] as LOG
  }
}

database "PostgreSQL" {
  [patients] as TBL_PAT
  [users] as TBL_USR
  [visits] as TBL_VIS
  [column_visibility] as TBL_COL
  [patient_columns_meta] as TBL_META
  [action_logs] as TBL_LOG
}

' --- Connections ---
UI --> AUTH : HTTP Requests
JS --> SEARCH : AJAX/Fetch
AUTH --> PATIENTS
AUTH --> HOSP
AUTH --> STATS

PATIENTS --> TBL_PAT : psycopg2\nRealDictCursor
HOSP --> TBL_PAT
SEARCH --> TBL_PAT
STATS --> TBL_PAT
STATS --> TBL_VIS

PATIENTS --> PDF : Generer facture
PATIENTS --> EMAIL : Notifier equipe
STATS --> GRAPH : Generer graphiques
PATIENTS --> LOG : Tracer actions

HASH --> TBL_USR : Verifier credentials
SMS ..> AUTH : Code de verification

@enduml
```

## Class Diagram (Simplified)

```mermaid
@startuml

class FlaskApp {
  +secret_key
  +routes[]
  --
  +index()
  +login()
  +verify_sms()
  +logout()
  +search()
  +add_patient()
  +update_patient()
  +delete_patient()
  +generate_invoice()
  +dashboard()
  +report()
}

class Authentication {
  -ph: PasswordHasher
  -PEPPER_ENV: str
  --
  +login_required(f): decorator
  +verify_password(hash, password): bool
  -_apply_pepper(password): str
}

class InvoicePDF {
  -MOIS_FR: dict
  --
  +header()
  +footer()
  +generate(patient_data)
}

class Database {
  -DATABASE_URL: str
  --
  +get_db_connection(): Connection
  +init_db()
}

class EmailService {
  -smtp_server: str
  -smtp_port: int
  -your_email: str
  --
  +email_reception(firstname, lastname, body, plot, recipient)
}

class DynamicColumns {
  --
  +get_visible_columns(): list
  +get_visibility_backend(role): list
  +manage_columns()
  +add_column()
  +toggle_column()
  +remove_column()
}

class Logging {
  --
  +log_file(user_type, action, details)
}

FlaskApp --> Authentication : uses
FlaskApp --> InvoicePDF : generates
FlaskApp --> Database : queries
FlaskApp --> EmailService : sends notifications
FlaskApp --> DynamicColumns : configures display
FlaskApp --> Logging : traces actions

@enduml
```

## Sequence Diagram - Patient Registration Flow

```mermaid
@startuml

actor "Utilisateur" as user
participant "Frontend\n(Jinja2 + JS)" as front
participant "Flask\n(app.py)" as flask
participant "Auth\n(login_required)" as auth
database "PostgreSQL" as db
participant "Email\nService" as email
participant "Logger" as log

== Authentification ==

user -> front : Acceder au site
front -> flask : GET /login
flask -> front : Page de connexion
user -> front : Saisir email + mot de passe
front -> flask : POST /login
flask -> db : SELECT FROM users
flask -> flask : verify_password(hash, input)
flask -> user : Rediriger vers /verify_sms
user -> front : Saisir code SMS
front -> flask : POST /verify_sms
flask -> flask : Valider code Twilio
flask -> front : Rediriger vers /

== Ajout d'un Patient ==

user -> front : Remplir formulaire patient
front -> flask : POST /add
flask -> auth : Verifier session
auth -> flask : OK
flask -> db : INSERT INTO patients
db -> flask : Patient cree (id)
flask -> email : Notifier l'equipe
flask -> log : log_file("ajout patient")
flask -> front : JSON {success: true}
front -> user : Patient ajoute

== Generation de Facture ==

user -> front : Cliquer "Generer facture"
front -> flask : POST /generate_invoice/{id}
flask -> auth : Verifier session
flask -> db : SELECT patient data
flask -> flask : InvoicePDF.generate()
flask -> front : Fichier PDF
front -> user : Telecharger la facture

@enduml
```
