# API and Postman guide

Base URL: `http://127.0.0.1:5000/api`. JSON requests and responses. The browser and Postman must retain the session cookie.

## Authentication sequence

1. `GET /session`. Save the returned `csrf` value and cookie.
2. `POST /login` with `{"email":"...","password":"..."}` and header `X-CSRF-Token: <csrf>`.
3. `GET /session` again: login rotates the CSRF token. Use this new token for all subsequent changes.
4. All POST/PATCH/PUT/DELETE requests need `Content-Type: application/json` and the CSRF header, including sign-in and registration. Sign-out clears the cookie session.

The bundled Postman collection saves the token from `GET /session` automatically. Fill the `email`, `password`, `doctor_id`, `appointment_id`, `patient_id`, and `start` collection variables. Run Session, Login, Session again, then the desired request. Use independent cookie jars/browser profiles to test different identities.

| Method | Route | Access | Body or query |
| --- | --- | --- | --- |
| GET | /session | Public | Current user, CSRF token, server date/time |
| POST | /register | Public | name, email, phone, password; role is always patient |
| POST | /login | Public | email, password |
| POST | /logout | Signed-in/browser session | `{}` |
| POST | /set-password | Invitation holder | token, password |
| GET | /doctors | Signed in | Admin sees inactive doctors too |
| POST | /doctors | Admin | name, specialty, email |
| PATCH | /doctors/:id | Admin | active: true/false |
| POST | /doctors/:id/invite | Admin | Resend invitation if password not yet set |
| GET | /doctors/:id/slots | Patient/admin | date=YYYY-MM-DD |
| GET | /availability | Doctor | Own hours and upcoming leave |
| POST | /availability | Doctor | weekday: 0–6 (Monday=0), start: HH:MM, end: HH:MM |
| DELETE | /availability/:id | Doctor | Own period; future bookings must first be resolved |
| POST | /leaves | Doctor | date: YYYY-MM-DD |
| DELETE | /leaves/:id | Doctor | Own leave; does not restore cancelled appointments |
| GET | /appointments | Signed in | Optional doctor, date, status filters; scope always enforced |
| POST | /appointments | Patient | doctor_id: integer, start: YYYY-MM-DDTHH:MM:SS |
| GET | /appointments/:id | Owner patient/doctor, admin | Metadata only; no notes |
| POST | /appointments/:id/reschedule | Owner patient | start |
| POST | /appointments/:id/status | Authorized role | status; optional note for completion/no-show |
| GET | /appointments/:id/note | Owner patient/doctor | Admin always denied |
| PUT | /appointments/:id/note | Owner doctor | note: up to 2,000 characters; after completion/no-show |
| GET | /patients | Admin/doctor | q search; doctor sees own patients |
| GET | /patients/:id/history | Owning doctor | Only that doctor's visits/notes |
| GET | /dashboard | Signed in | Role-scoped totals; admin also gets per-doctor counts |

## Status changes

- Patient creates `Pending`.
- Doctor: `Pending → Confirmed` or `Pending → Rejected`, only before the start.
- Doctor: `Confirmed → Completed` or `Confirmed → No-show`, only at/after start.
- Patient: `Pending/Confirmed → Cancelled` at least 2 hours before start.
- Admin: `Pending/Confirmed → Cancelled` without patient cutoff.
- Leave/expiry/deactivation: permitted active appointments → `Cancelled`.
- Reschedule: `Pending/Confirmed → Pending` with a new start and incremented revision.
- Terminal statuses cannot be reopened.

Errors return `{"error":"clear message"}`. Codes: 400 invalid business operation, 401 unsigned-in/inactive session, 403 forbidden/CSRF, 404 unavailable entity, 409 conflicting booking/account/hours, 429 throttled sign-in. Direct API requests receive exactly the same rule checks as the UI.
