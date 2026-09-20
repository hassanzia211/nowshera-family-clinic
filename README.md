# Nowshera Family Clinic

A complete local full-stack Clinic Appointment & Patient Management System with separate patient, doctor, and clinic-admin workspaces.

**Stack:** Flask JSON API · SQLite database · responsive HTML/CSS/JavaScript frontend · Python email/automation worker · Waitress server.

## Start on Windows — quickest route

1. Install **Python 3.11 or newer**, with **Add Python to PATH** checked.
2. Extract this ZIP completely. Do not run the launcher from inside the ZIP preview.
3. Double-click **START-WINDOWS.bat**. Internet is needed for the first dependency installation.
4. A text file opens with your generated demo password and account emails. The browser opens at **http://127.0.0.1:5000**.
5. Keep the terminal window open while using the website. The website and automatic jobs run in this process.

If Windows asks whether to open the batch file, inspect it in a text editor first. It creates a local Python environment, installs requirements, creates demo accounts only if the database is empty, and starts the server.

**Already have Python and prefer PowerShell?** From the extracted project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py demo
notepad instance\DEMO-LOGINS.txt
.\.venv\Scripts\python.exe run.py
```

No activation script is needed. This avoids PowerShell execution-policy problems.

Linux/macOS: run `bash start.sh`, then open http://127.0.0.1:5000. Read `instance/DEMO-LOGINS.txt` for the generated password.

## Demo accounts

| Role | Email |
| --- | --- |
| Admin | admin@clinic.test |
| Doctor — Family Medicine | ayesha@clinic.test |
| Doctor — Cardiology | hamza@clinic.test |
| Doctor — Pediatrics | sana@clinic.test |
| Patient | patient@clinic.test |
| Second patient | patient2@clinic.test |

The launcher generates a fresh random demo password on first setup. Read it in `instance/DEMO-LOGINS.txt`. The same password is used for these **local demonstration accounts only**. These addresses are placeholders and do not receive real email.

Seeded doctors work Monday–Saturday, 09:00–13:00 and 15:00–18:00. Sunday intentionally has no slots. Choose a future working day for your demonstration. Newly invited doctors have **no default hours** and must add them.

No appointment fixtures are inserted into the delivered database. Dashboard totals reflect bookings you actually make. Screenshots show demonstration data created during browser verification.

## Real emails: one required configuration step

**The default is local email demonstration mode. It does not deliver email to an inbox.** Generated `.eml` messages and easy-to-read `.txt` copies are saved in `instance/outbox/`. Double-click `OPEN-LOCAL-EMAILS.bat`, then open a `.txt` copy in Notepad to inspect it or copy its complete invitation link. For a new doctor, the message contains a one-use password link; copy the complete `http://127.0.0.1:5000/#invite=...` URL into the browser on the same computer.

To send real invitations, confirmations, rejections, cancellations, and reminders:

1. Copy `.env.example` to `.env` in the project root.
2. Set your provider's SMTP STARTTLS settings, for example:

```dotenv
MAIL_MODE=smtp
SMTP_HOST=your-provider-smtp-host
SMTP_PORT=587
SMTP_USER=your-provider-username
SMTP_PASSWORD=your-provider-app-password
SMTP_FROM=your-verified-sender@example.com
SMTP_TLS=true
BASE_URL=http://127.0.0.1:5000
```

3. Restart `run.py` / the launcher. Register patients and invite doctors with real addresses.
4. Perform a **new** confirmation/invitation and check delivery. Previously saved local-demo messages are intentionally not resent.

Use the provider's application password when required, not a password pasted into source code. `.env`, the database, signing secret, and demo credentials are excluded by `.gitignore`.

**External SMTP inbox delivery has not been verified with your account.** The outbox and SMTP adapter were tested locally, with a fake SMTP transport in automated tests. The assignment's real-email checks require valid credentials and actual recipient testing.

Local invitation links work only on the computer running the clinic server. A remote doctor needs a deployed HTTPS URL and a suitable server configuration; external deployment is outside the local assignment deliverable.

## Feature coverage

- Patient registration with name, phone, and email; hashed passwords; sign-in/sign-out.
- Admin doctor creation and single-use, 24-hour password invitations; resending unused invitations; activation/deactivation.
- Active doctor directory, specialty, date selection, and free 30-minute slots.
- Pending bookings hold the slot immediately; database constraints block doctor and patient time conflicts.
- Server validation rejects past times, off-grid times, unavailable doctors, leave days, and times outside working hours.
- Doctor weekly working periods with overlap validation. Removing a period with future active bookings is blocked.
- Doctor leave cancels all Pending/Confirmed appointments on that date in one transaction and queues cancellation emails.
- Doctor confirmation/rejection; only Confirmed appointments can become Completed or No-show, and only once their time starts.
- Patient cancellation/rescheduling allowed **at least** 2 hours before the original start, including exactly 2 hours. A successful reschedule becomes Pending and releases the old slot atomically.
- Admin cancellation of any Pending/Confirmed appointment; terminal history is preserved.
- Doctor deactivation blocks sign-in and future bookings and cancels future active appointments with email notification.
- Private visit notes available only to the appointment's patient and doctor. Admin appointment/list/dashboard responses never include note text.
- Doctor history includes only appointments between that doctor and that patient.
- Admin contact search, doctor/date/status appointment filters, today's schedule, and per-doctor status counts.
- Persistent database, responsive sidebar navigation, loading/empty/error states, keyboard-accessible forms and dialogs.

## Automated jobs

`python run.py` starts a background worker automatically. Every 30 seconds it:

1. Cancels Pending requests whose appointment start has passed.
2. Queues a reminder for each Confirmed appointment dated tomorrow in **Asia/Karachi**.
3. Processes up to 50 queued emails, retrying failed deliveries on later cycles.

To run a cycle immediately, from a second terminal:

```powershell
.\.venv\Scripts\python.exe manage.py automations
```

The server must remain running for automatic work. Overdue Pending requests are cancelled on startup after downtime. A reminder window missed because the computer was off is not backfilled after the appointment day begins.

Unique event keys prevent repeated automation runs from queuing duplicate reminders/cancellations. Each reschedule starts a new appointment revision, so a later confirmation and reminder can be sent again. SMTP cannot guarantee exactly-once delivery if a process crashes after the provider accepts an email but before the local database commits; Message-ID is stable, but provider deduplication is not guaranteed. Routine repeated runs are covered by tests.

## Tests and submission

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

See **docs/TEST-REPORT.md** for the recorded results and assignment coverage, **docs/DEMO-SCRIPT.md** for a presentation walkthrough, and **docs/API.md** for API/Postman instructions. A ready-to-import Postman collection is provided in `docs/Clinic.postman_collection.json`.

Test databases are temporary. Tests do not alter your local demo database.

## Project layout

```text
app/
  __init__.py       App factory, sessions, CSRF, response security
  db.py             SQLite connection management
  schema.sql        Tables, foreign keys, unique booking constraints
  domain.py         Booking rules, permissions, notifications, expiry
  routes.py         Role-protected JSON API
  automation.py     Durable outbox, SMTP/file transport, scheduled jobs
  templates/        Main page shell
  static/           Responsive frontend and interface styles
manage.py           Demo setup, manual admin creation, job invocation
run.py              Local Waitress server and worker lifecycle
START-WINDOWS.bat    Windows setup and launch
start.sh            Linux/macOS setup and launch
requirements.txt    Python dependencies
tests/              Automated acceptance and security tests
docs/               API, testing, architecture, demo script
```

## Persistence and administration

All runtime data lives in `instance/clinic.db`; closing the browser or refreshing does not clear it. Keep `instance/.secret` stable so session signing survives restarts. To back up the demo, stop the server and copy the whole `instance` folder to a private location.

For a clean non-demo installation, do not run `manage.py demo`; instead create an admin with `python manage.py admin`, then start `python run.py`. The admin command prompts for your password without displaying it. Do not publish runtime files or use real clinical information in this coursework demo.

## Design decisions and boundaries

This project deliberately uses one same-origin app and SQLite to minimize setup time for a local submission. It does not require Node.js, Supabase credentials, n8n, or an external database. Python handles the automation requirement. The frontend communicates with a real backend API; business rules are never trusted to the browser.

The appointment grid is aligned to :00/:30 and uses Pakistan local time, appropriate for the single Nowshera branch. Availability does not support overnight periods; add separate days instead. Rejected is stored and shown separately from Cancelled. Dashboard status totals are all-time; the "today" card is date-scoped. Admin note privacy applies to application users, not a person who has operating-system/database administrator access.

Before real public clinical use, this coursework project would need a deployment/security review, HTTPS, backup and recovery procedures, broader abuse controls, and privacy/compliance evaluation. No healthcare compliance certification is claimed. Payments, prescriptions, lab reports, billing, video calls, SMS/WhatsApp, mobile apps, and multiple branches are intentionally excluded.

## Implementation references

The database uses unique partial indexes to restrict conflicting slot rows: [SQLite documentation](https://www.sqlite.org/partialindex.html). Session cookie settings, content security policy, escaped rendering, and explicit CSRF checks follow the concerns documented in [Flask security considerations](https://flask.palletsprojects.com/en/stable/web-security/).
