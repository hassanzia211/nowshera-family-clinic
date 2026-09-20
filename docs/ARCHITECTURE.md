# Architecture and rule enforcement

The frontend fetches a same-origin JSON API using an HttpOnly signed session cookie. It keeps no appointment database in browser storage. SQLite is the durable authority.

## Data model

- `users`: identity, hashed password, role, contact details, doctor specialty/active state.
- `availability`: doctor, weekday, starting and ending clock times.
- `leaves`: unique doctor/date combinations.
- `appointments`: patient, doctor, start, state, reason, revision, creation time.
- `notes`: separate private text keyed by appointment.
- `invitations`: hashed token, doctor, expiration, used flag. Raw invitation tokens are only in email content.
- `outbox`: unique event key, recipient, subject/body, delivery state and attempts.
- `audit`: actor, action, appointment, timestamp; contains no visit-note text.
- `login_attempts`: rate-limit state for email/IP combinations.

## Transactions and races

Every API mutation opens `BEGIN IMMEDIATE` before looking up the active user and validating business rules. Availability, leave, appointment writes, status changes, and notification inserts therefore serialize against other writers. Cancellation and rescheduling release the old slot in the same transaction as the state change. A failed operation rolls back and retains the original reservation.

Two database-level partial unique indexes additionally protect `(doctor_id,start)` and `(patient_id,start)` while an appointment is Pending, Confirmed, Completed, or No-show. Cancelled and Rejected rows remain as history but no longer reserve a slot. The fixed 30-minute grid makes identical start times equivalent to conflicting visits. Parallel-request testing verifies that only one of two competing patients succeeds.

## Access boundaries

User role is loaded from the database on every request, not trusted from form payloads. Doctor and patient queries are scoped by identity. Notes require an explicit role and ownership check before any note query; they are omitted entirely from generic appointment serializers. Admin cannot access the note or doctor-history endpoints. Patients cannot register as admins/doctors by changing JSON.

CSRF is checked for all unsafe methods. Passwords use Werkzeug's salted hash function. Invitation tokens use cryptographic random generation and hash storage. Login failures are throttled; account activity is rechecked even for an existing session. CSP and escaped user text protect rendered HTML. SQL values are parameterized.

## Automation

One daemon worker in `run.py` runs every 30 seconds. Domain automation opens a transaction, performs expiration and reminder enqueueing, then commits. Delivery processes each outbox row under a database write lock, so simultaneous workers cannot normally send the same row concurrently. Local `.eml` filenames are deterministic and replaced atomically. SMTP uses STARTTLS with default certificate validation. Failed sends retain `queued` state and do not lose the booking event.

This local design keeps implementation and setup small. SQLite writes may wait while an SMTP delivery holds the write lock. At larger scale, move to a database/queue with per-row claiming, leases, backoff, and a managed email service. Network-level exactly-once email cannot be guaranteed across an ambiguous provider timeout or a crash after delivery but before commit.
