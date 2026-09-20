PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
 phone TEXT NOT NULL DEFAULT '', password TEXT, role TEXT NOT NULL CHECK(role IN ('patient','doctor','admin')),
 specialty TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS availability (
 id INTEGER PRIMARY KEY, doctor_id INTEGER NOT NULL REFERENCES users(id), weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
 start TEXT NOT NULL, end TEXT NOT NULL, CHECK(start < end)
);
CREATE TABLE IF NOT EXISTS leaves (
 id INTEGER PRIMARY KEY, doctor_id INTEGER NOT NULL REFERENCES users(id), date TEXT NOT NULL, UNIQUE(doctor_id,date)
);
CREATE TABLE IF NOT EXISTS appointments (
 id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL REFERENCES users(id), doctor_id INTEGER NOT NULL REFERENCES users(id),
 start TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('Pending','Confirmed','Rejected','Cancelled','Completed','No-show')),
 reason TEXT NOT NULL DEFAULT '', revision INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS doctor_slot ON appointments(doctor_id,start) WHERE status IN ('Pending','Confirmed','Completed','No-show');
CREATE UNIQUE INDEX IF NOT EXISTS patient_slot ON appointments(patient_id,start) WHERE status IN ('Pending','Confirmed','Completed','No-show');
CREATE TABLE IF NOT EXISTS notes (appointment_id INTEGER PRIMARY KEY REFERENCES appointments(id), body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS invitations (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS outbox (
 id INTEGER PRIMARY KEY, event_key TEXT UNIQUE NOT NULL, recipient TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, sent_at TEXT
);
CREATE TABLE IF NOT EXISTS login_attempts (key TEXT PRIMARY KEY, count INTEGER NOT NULL, window TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, actor_id INTEGER, action TEXT NOT NULL, appointment_id INTEGER, created_at TEXT NOT NULL);
