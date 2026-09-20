from datetime import datetime
import pytest
from werkzeug.security import generate_password_hash
from app import create_app
from app.db import db


@pytest.fixture
def app(tmp_path):
    clock = [datetime(2026, 9, 20, 8, 0)]
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.db"),
            "INSTANCE_DIR": str(tmp_path),
            "SECRET_KEY": "test-key",
            "NOW": lambda: clock[0],
            "MAIL_MODE": "file",
        }
    )
    app.clock = clock
    with app.app_context():
        conn = db()
        for uid, role in [
            (1, "admin"),
            (2, "doctor"),
            (3, "doctor"),
            (4, "patient"),
            (5, "patient"),
        ]:
            conn.execute(
                "INSERT INTO users(id,name,email,phone,password,role,specialty,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    uid,
                    f"User {uid}",
                    f"user{uid}@example.com",
                    "03001234567",
                    generate_password_hash("Password123!"),
                    role,
                    "Family Medicine" if role == "doctor" else "",
                    clock[0].isoformat(),
                ),
            )
        for uid in (2, 3):
            for day in range(7):
                conn.execute(
                    "INSERT INTO availability(doctor_id,weekday,start,end) VALUES(?,?,?,?)",
                    (uid, day, "09:00", "11:00"),
                )
    return app


@pytest.fixture
def clients(app):
    result = {}
    for uid in range(1, 6):
        client = app.test_client()
        with client.session_transaction() as session:
            session.update(uid=uid, csrf="token")
        result[uid] = client
    return result


def send(client, path, payload=None, method="POST"):
    return client.open(
        "/api" + path,
        method=method,
        json=payload or {},
        headers={"X-CSRF-Token": "token"},
    )


def book(client, doctor=2, start="2026-09-21T09:00:00"):
    response = send(client, "/appointments", {"doctor_id": doctor, "start": start})
    assert response.status_code == 201, response.json
    return response.json["id"]
