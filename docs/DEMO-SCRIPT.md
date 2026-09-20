# Submission walkthrough — approximately 6 minutes

Use only demonstration records. Open a normal browser for admin and an incognito window for a patient/doctor, or sign out between roles.

1. **Architecture (20 seconds):** “This is a full-stack appointment system. The frontend calls a Flask API. SQLite persists data. A Python worker handles emails, reminders and expired requests.”
2. **Patient (60 seconds):** Sign in as patient. Open Find a doctor, choose Dr. Ayesha, choose tomorrow or the next working day, pick a slot, and request it. Show Pending. Refresh and show the same booking still exists.
3. **Doctor (45 seconds):** Sign in as Ayesha. Open Appointments, view the request, and confirm. Open My availability and explain the 30-minute schedule.
4. **Admin (40 seconds):** Sign in as admin. Show per-doctor status counts. Filter appointments by doctor and date. Open Patients and search by name. Open the appointment: there is no clinical note action for admin.
5. **Invitation (45 seconds):** Add a doctor with a unique email. Wait up to 30 seconds or run `manage.py automations`. In file mode, open the new `instance/outbox/*.eml` message and use its invitation link. Set a password, sign in as the new doctor, and add Monday 09:00–11:00 hours. Explain that SMTP configuration changes local demo output to real email.
6. **Rules (60 seconds):** Use Postman to request the occupied slot as patient 2, then try the original patient's same time with a different doctor. Show both 409 errors. Show test output for wrong roles, private notes, past slots and the cutoff.
7. **Leave and automation (45 seconds):** As Ayesha add leave on the booked day. Show cancellation, no slots, and the cancellation email. Run automation twice and show no new duplicate reminder/cancellation rows.
8. **Mobile and finish (25 seconds):** Open browser responsive mode at 390px. Show mobile menu and appointment screen. Explain local persistence and the 16 passing automated checks.

For a completed visit and private note demo without waiting, use a real current-day confirmed appointment once its time starts. Automated tests use an isolated controlled clock for these edge cases; the delivered app does not expose a time-travel endpoint or allow early completion.

## Before recording

- Do not show `.env`, SMTP credentials, invitation tokens, or demo passwords on a public video.
- If using local email mode, label it honestly; actual inbox delivery is not demonstrated until SMTP is configured.
- Read `TEST-REPORT.md`. Do not claim all real-email acceptance checks have been completed when only `.eml` output was verified.
