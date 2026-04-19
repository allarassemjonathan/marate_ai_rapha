# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Marate AI Rapha is a medical patient management system for a dental clinic ("Cabinet RAPHA"). It's a monolithic Flask application (~2400 lines in app.py) with PostgreSQL backend, role-based access control, PDF invoice generation, email notifications, and SMS 2FA via Twilio.

## Commands

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run (development)
python3 -m flask run
# or: gunicorn app:app (production)

# Tests
python3 run_tests.py                       # Full suite with coverage
pytest tests/ -v                           # All tests verbose
pytest tests/test_auth.py -v               # Single test file
pytest tests/test_auth.py::TestAuthentication::test_login_success -v  # Single test
```

## Required Environment Variables (.env)

DATABASE_URL, FLASK_SECRET, SMTP_SERVER, SMTP_PORT, EMAIL, CODE, NURSES_EMAIL, PHYSI_EMAIL, account_sid, auth_token, PEPPER_ENV, APP_PASSWORD_PEPPER, cabinet, manager

## Architecture

**Single-file Flask app** (`app.py`) with all routes, models, and business logic:

- **Database**: PostgreSQL via `psycopg2` with `RealDictCursor`. Connection pattern: `get_db_connection()` returns a connection, use `autocommit=True`, parameterized queries with `%s` placeholders. Tables: `patients`, `users`, `column_visibility`, `patient_columns_meta`, `visits`, `action_logs`.
- **Auth**: Argon2 password hashing with pepper (`PEPPER_ENV`). SMS 2FA via Twilio on 180-day cycle. Session-based with `login_required` decorator. Three roles: `medecins` (doctors), `infirmiers` (nurses), `receptionistes` (receptionists).
- **Doctor ownership**: Doctors can only view/modify patients they signed. Nurses and receptionists have no ownership restriction. The `manager` env var grants admin access to all patients.
- **PDF generation**: `InvoicePDF` class extends `FPDF` from fpdf2. Loads logos from remote URLs, calculates insurance/patient payment splits. Route: `POST /generate_invoice/<id>`.
- **Email**: SMTP via Gmail with app passwords. `email_reception()` sends HTML emails with optional matplotlib plot attachments.
- **Dynamic columns**: Patient table schema can be modified at runtime via `/manage_columns`. Column visibility is per-role via JSON arrays in `column_visibility` table.
- **Logging**: File-based (`daily_log.txt`) via `log_file()`. Logs login, CRUD, invoice generation, etc.

**Frontend**: Jinja2 templates + vanilla JS (`static/js/search.js` handles patient list rendering, search, CRUD). Tailwind CSS.

## Key Patterns

- Empty strings for numeric fields are converted to `None` before DB insert
- Age stored as composite: `age_years`, `age_months`, `age_days` → calculated `age` field
- French locale (`fr_FR.UTF-8`) used for date formatting
- Mixed French/English in code and variable names
- `requirements.txt` lists `fpdf` but the actual package needed is `fpdf2` (imports as `fpdf`)

## Testing

Tests use `pytest` with `unittest.mock`. Fixtures in `tests/conftest.py` provide: `client`, `mock_db_connection` (patches `get_db_connection`), `authenticated_session`, `nurse_session`, `receptionist_session`. DB connections are always mocked — tests never hit a real database. PDF and email operations are also mocked.
