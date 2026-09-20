from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from email import policy
from email.parser import BytesParser
import re
from app.db import db
from app.automation import tick
from conftest import send, book


def test_01_book_confirm_and_email(app, clients):
    aid = book(clients[4])
    assert (
        clients[4].get(f"/api/appointments/{aid}").json["appointment"]["status"]
        == "Pending"
    )
    assert (
        send(
            clients[2], f"/appointments/{aid}/status", {"status": "Confirmed"}
        ).status_code
        == 200
    )
    tick(app)
    with app.app_context():
        row = (
            db()
            .execute("SELECT * FROM outbox WHERE subject LIKE ?", ("%Confirmed%",))
            .fetchone()
        )
        assert row["recipient"] == "user4@example.com" and row["state"] == "saved-local"
        assert "note" not in row["body"].lower()


def test_02_doctor_invitation_password_hours_and_dashboard(app, clients):
    response = send(
        clients[1],
        "/doctors",
        {"name": "Dr New", "email": "new@example.com", "specialty": "Pediatrics"},
    )
    assert response.status_code == 201
    uid = response.json["id"]
    tick(app)
    with app.app_context():
        row = (
            db()
            .execute("SELECT * FROM outbox WHERE recipient='new@example.com'")
            .fetchone()
        )
        token = row["body"].split("#invite=")[1]
        assert (
            db()
            .execute("SELECT password FROM users WHERE id=?", (uid,))
            .fetchone()["password"]
            is None
        )
    client = app.test_client()
    csrf = client.get("/api/session").json["csrf"]
    response = client.post(
        "/api/set-password",
        json={"token": token, "password": "NewPassword123!"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert (
        client.post(
            "/api/set-password",
            json={"token": token, "password": "NewPassword123!"},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/login",
            json={"email": "new@example.com", "password": "NewPassword123!"},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 200
    )
    with client.session_transaction() as s:
        s["csrf"] = "token"
    assert (
        send(
            client, "/availability", {"weekday": 0, "start": "09:00", "end": "11:00"}
        ).status_code
        == 201
    )
    assert (
        len(clients[4].get(f"/api/doctors/{uid}/slots?date=2026-09-21").json["slots"])
        == 4
    )
    book(clients[4], uid)
    for _ in range(2):
        doctor = next(
            d
            for d in clients[1].get("/api/dashboard").json["doctors"]
            if d["id"] == uid
        )
        assert doctor["counts"]["Pending"] == 1


def test_03_same_doctor_and_same_patient_time_conflicts(app, clients):
    book(clients[4])
    assert (
        send(
            clients[5],
            "/appointments",
            {"doctor_id": 2, "start": "2026-09-21T09:00:00"},
        ).status_code
        == 409
    )
    assert (
        send(
            clients[4],
            "/appointments",
            {"doctor_id": 3, "start": "2026-09-21T09:00:00"},
        ).status_code
        == 409
    )
    with app.app_context():
        assert db().execute("SELECT count(*) FROM appointments").fetchone()[0] == 1


def test_03b_simultaneous_booking_is_atomic(app, clients):
    def attempt(uid):
        return send(
            clients[uid],
            "/appointments",
            {"doctor_id": 2, "start": "2026-09-21T09:00:00"},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [4, 5]))
    assert sorted(results) == [201, 409]


def test_04_outside_hours_fully_booked_and_alignment(app, clients):
    for start in ["2026-09-21T08:30:00", "2026-09-21T11:00:00", "2026-09-21T09:15:00"]:
        assert (
            send(
                clients[4], "/appointments", {"doctor_id": 2, "start": start}
            ).status_code
            == 400
        )
    for hour in ["09:00", "09:30", "10:00", "10:30"]:
        book(clients[4], start="2026-09-21T" + hour + ":00")
    assert clients[5].get("/api/doctors/2/slots?date=2026-09-21").json["slots"] == []


def test_05_past_inactive_early_completion_and_leave(app, clients):
    assert (
        send(
            clients[4],
            "/appointments",
            {"doctor_id": 2, "start": "2026-09-19T09:00:00"},
        ).status_code
        == 400
    )
    aid = book(clients[4])
    send(clients[2], f"/appointments/{aid}/status", {"status": "Confirmed"})
    assert (
        send(
            clients[2], f"/appointments/{aid}/status", {"status": "Completed"}
        ).status_code
        == 400
    )
    assert send(clients[1], "/doctors/3", {"active": False}, "PATCH").status_code == 200
    assert (
        send(
            clients[4],
            "/appointments",
            {"doctor_id": 3, "start": "2026-09-21T10:00:00"},
        ).status_code
        == 404
    )
    assert send(clients[2], "/leaves", {"date": "2026-09-21"}).json["cancelled"] == 1
    assert (
        clients[4].get(f"/api/appointments/{aid}").json["appointment"]["status"]
        == "Cancelled"
    )
    assert clients[4].get("/api/doctors/2/slots?date=2026-09-21").json["slots"] == []
    tick(app)
    with app.app_context():
        assert (
            db()
            .execute(
                "SELECT count(*) FROM outbox WHERE subject LIKE '%Cancelled%' AND state='saved-local'"
            )
            .fetchone()[0]
            == 1
        )


def test_06_cancel_reschedule_and_two_hour_boundary(app, clients):
    aid = book(clients[4])
    send(clients[2], f"/appointments/{aid}/status", {"status": "Confirmed"})
    assert (
        send(
            clients[4], f"/appointments/{aid}/status", {"status": "Cancelled"}
        ).status_code
        == 200
    )
    second = book(clients[5])
    send(clients[2], f"/appointments/{second}/status", {"status": "Confirmed"})
    assert (
        send(
            clients[5],
            f"/appointments/{second}/reschedule",
            {"start": "2026-09-21T10:00:00"},
        ).status_code
        == 200
    )
    assert (
        clients[5].get(f"/api/appointments/{second}").json["appointment"]["status"]
        == "Pending"
    )
    third = book(clients[4])
    app.clock[0] = datetime(2026, 9, 21, 7, 0, 1)
    assert (
        send(
            clients[4], f"/appointments/{third}/status", {"status": "Cancelled"}
        ).status_code
        == 400
    )
    assert (
        send(
            clients[4],
            f"/appointments/{third}/reschedule",
            {"start": "2026-09-22T09:00:00"},
        ).status_code
        == 400
    )
    app.clock[0] = datetime(2026, 9, 21, 7, 0)
    assert (
        send(
            clients[4], f"/appointments/{third}/status", {"status": "Cancelled"}
        ).status_code
        == 200
    )


def test_06b_failed_reschedule_preserves_original(app, clients):
    aid = book(clients[4])
    book(clients[5], start="2026-09-21T10:00:00")
    assert (
        send(
            clients[4],
            f"/appointments/{aid}/reschedule",
            {"start": "2026-09-21T10:00:00"},
        ).status_code
        == 409
    )
    assert (
        clients[4].get(f"/api/appointments/{aid}").json["appointment"]["start"]
        == "2026-09-21T09:00:00"
    )


def test_07_invalid_hours_overlap_and_past_leave(clients):
    assert (
        send(
            clients[2],
            "/availability",
            {"weekday": 0, "start": "13:00", "end": "09:00"},
        ).status_code
        == 400
    )
    assert (
        send(
            clients[2],
            "/availability",
            {"weekday": 0, "start": "10:30", "end": "12:00"},
        ).status_code
        == 409
    )
    assert (
        send(
            clients[2],
            "/availability",
            {"weekday": 0, "start": "09:15", "end": "12:00"},
        ).status_code
        == 400
    )
    assert send(clients[2], "/leaves", {"date": "2026-09-19"}).status_code == 400
    assert (
        send(
            clients[2],
            "/availability",
            {"weekday": 0, "start": "11:00", "end": "12:00"},
        ).status_code
        == 201
    )


def test_08_role_and_cross_doctor_guards(clients):
    aid = book(clients[4])
    for uid in [4, 3]:
        assert (
            send(
                clients[uid], f"/appointments/{aid}/status", {"status": "Confirmed"}
            ).status_code
            == 403
        )
    assert (
        send(
            clients[4],
            "/doctors",
            {"name": "Bad", "email": "bad@example.com", "specialty": "Test"},
        ).status_code
        == 403
    )
    assert (
        clients[4].get(f"/api/appointments/{aid}").json["appointment"]["status"]
        == "Pending"
    )


def test_09_private_notes_and_scoped_history(app, clients):
    aid = book(clients[4])
    send(clients[2], f"/appointments/{aid}/status", {"status": "Confirmed"})
    app.clock[0] = datetime(2026, 9, 21, 9, 0)
    assert (
        send(
            clients[2],
            f"/appointments/{aid}/status",
            {"status": "Completed", "note": "Private medical visit note."},
        ).status_code
        == 200
    )
    for uid in [1, 3, 5]:
        assert clients[uid].get(f"/api/appointments/{aid}/note").status_code == 403
    assert clients[5].get(f"/api/appointments/{aid}").status_code == 403
    assert clients[3].get("/api/patients/4/history").status_code == 403
    for path in [
        "/api/appointments",
        f"/api/appointments/{aid}",
        "/api/dashboard",
        "/api/patients",
    ]:
        assert b"Private medical visit note" not in clients[1].get(path).data
    assert (
        clients[4].get(f"/api/appointments/{aid}/note").json["note"]
        == "Private medical visit note."
    )
    assert (
        clients[2].get("/api/patients/4/history").json["history"][0]["note"]
        == "Private medical visit note."
    )


def test_10_reminder_expiration_repeat_and_persistence(app, clients):
    aid = book(clients[4])
    send(clients[2], f"/appointments/{aid}/status", {"status": "Confirmed"})
    pending = book(clients[5], start="2026-09-20T09:00:00")
    app.clock[0] = datetime(2026, 9, 20, 9, 1)
    tick(app)
    tick(app)
    with app.app_context():
        assert (
            db()
            .execute("SELECT count(*) FROM outbox WHERE subject LIKE '%Reminder%'")
            .fetchone()[0]
            == 1
        )
        assert (
            db()
            .execute("SELECT count(*) FROM outbox WHERE subject LIKE '%Cancelled%'")
            .fetchone()[0]
            == 1
        )
        assert all(
            r["state"] == "saved-local"
            for r in db().execute("SELECT state FROM outbox")
        )
    for _ in range(2):
        assert (
            clients[5].get(f"/api/appointments/{pending}").json["appointment"]["status"]
            == "Cancelled"
        )


def test_auth_csrf_logout_and_deactivation(app, clients):
    anonymous = app.test_client()
    assert anonymous.get("/api/appointments").status_code == 401
    assert clients[4].post("/api/appointments", json={}).status_code == 403
    assert send(clients[4], "/logout").status_code == 200
    assert clients[4].get("/api/appointments").status_code == 401
    assert send(clients[1], "/doctors/2", {"active": False}, "PATCH").status_code == 200
    assert clients[2].get("/api/availability").status_code == 401


def test_registration_validation_and_role_escalation(app):
    client = app.test_client()
    csrf = client.get("/api/session").json["csrf"]
    headers = {"X-CSRF-Token": csrf}
    payload = {
        "name": "New Patient",
        "email": "newpatient@example.com",
        "phone": "03001234567",
        "password": "StrongPassword123!",
        "role": "admin",
    }
    assert (
        client.post("/api/register", json=payload, headers=headers).status_code == 201
    )
    assert client.get("/api/session").json["user"]["role"] == "patient"
    assert client.get("/api/patients").status_code == 403


def test_expired_invitation_and_no_slot_leak_on_leave(app, clients):
    send(
        clients[1],
        "/doctors",
        {"name": "Dr Invite", "email": "invite@example.com", "specialty": "Test"},
    )
    with app.app_context():
        token = (
            db()
            .execute("SELECT body FROM outbox WHERE recipient='invite@example.com'")
            .fetchone()[0]
            .split("#invite=")[1]
        )
    app.clock[0] = datetime(2026, 9, 22, 8)
    assert (
        send(
            clients[1], "/set-password", {"token": token, "password": "Password123!"}
        ).status_code
        == 400
    )


def test_smtp_transport_is_tested_without_external_email(app, clients, monkeypatch):
    deliveries = []

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def ehlo(self):
            pass

        def starttls(self, context):
            pass

        def login(self, user, password):
            pass

        def send_message(self, msg):
            deliveries.append(msg)

    monkeypatch.setattr("app.automation.smtplib.SMTP", FakeSMTP)
    app.config.update(MAIL_MODE="smtp", SMTP_HOST="smtp.example.com")
    aid = book(clients[4])
    send(clients[2], f"/appointments/{aid}/status", {"status": "Confirmed"})
    tick(app)
    tick(app)
    assert len(deliveries) == 2  # confirmation and tomorrow's reminder, once each
    assert all(msg["To"] == "user4@example.com" for msg in deliveries)
