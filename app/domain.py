"""Booking invariants shared by HTTP handlers and scheduled automation."""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import current_app, g
from .db import db

ACTIVE = ("Pending", "Confirmed")
STATUSES = ("Pending", "Confirmed", "Completed", "No-show", "Cancelled", "Rejected")


class Problem(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def now():
    clock = current_app.config.get("NOW")
    return (
        clock()
        if clock
        else datetime.now(ZoneInfo(current_app.config["CLINIC_TIMEZONE"])).replace(
            tzinfo=None
        )
    )


def stamp():
    return now().isoformat(timespec="seconds")


def require(*roles):
    if not g.user:
        raise Problem("Please sign in to continue.", 401)
    if roles and g.user["role"] not in roles:
        raise Problem("You do not have permission for this action.", 403)
    return g.user


def text(data, key, limit=200, required=True):
    value = data.get(key, "")
    if (
        not isinstance(value, str)
        or len(value) > limit
        or (required and not value.strip())
    ):
        raise Problem(
            f'Enter a valid {key.replace("_"," ")} (maximum {limit} characters).'
        )
    return value.strip()


def email(data):
    value = text(data, "email", 254).lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise Problem("Enter a valid email address.")
    return value


def password(data):
    value = text(data, "password", 128)
    if len(value) < 10:
        raise Problem("Use a password with at least 10 characters.")
    return value


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise Problem("Enter a valid date (YYYY-MM-DD).")


def parse_start(value):
    try:
        result = datetime.fromisoformat(value)
        if (
            result.tzinfo
            or result.second
            or result.microsecond
            or result.minute not in (0, 30)
        ):
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise Problem("Choose a 30-minute clinic slot. All times are Pakistan time.")


def doctor(doctor_id, active=False):
    row = (
        db()
        .execute(
            "SELECT id,name,specialty,email,active FROM users WHERE id=? AND role='doctor'",
            (doctor_id,),
        )
        .fetchone()
    )
    if not row or (active and not row["active"]):
        raise Problem("This doctor is unavailable for booking.", 404)
    return row


def validate_slot(doctor_id, patient_id, start, exclude=0):
    doctor(doctor_id, True)
    if start <= now():
        raise Problem("Appointments must be in the future.")
    day = start.date().isoformat()
    if (
        db()
        .execute("SELECT 1 FROM leaves WHERE doctor_id=? AND date=?", (doctor_id, day))
        .fetchone()
    ):
        raise Problem("The doctor is on leave on this date.")
    windows = (
        db()
        .execute(
            "SELECT * FROM availability WHERE doctor_id=? AND weekday=?",
            (doctor_id, start.weekday()),
        )
        .fetchall()
    )
    if not any(
        datetime.fromisoformat(day + "T" + w["start"]) <= start
        and start + timedelta(minutes=30)
        <= datetime.fromisoformat(day + "T" + w["end"])
        for w in windows
    ):
        raise Problem("That time is outside the doctor's working hours.")
    booked = (
        db()
        .execute(
            "SELECT doctor_id,patient_id FROM appointments WHERE start=? AND id!=? AND status IN ('Pending','Confirmed','Completed','No-show') AND (doctor_id=? OR patient_id=?)",
            (start.isoformat(timespec="seconds"), exclude, doctor_id, patient_id),
        )
        .fetchone()
    )
    if booked:
        raise Problem(
            (
                "You already have an appointment at this time."
                if booked["patient_id"] == patient_id
                else "Someone has already taken this slot. Please choose another."
            ),
            409,
        )


def appointment(aid):
    row = (
        db()
        .execute(
            """SELECT a.*, p.name patient_name,p.email patient_email,p.phone patient_phone,d.name doctor_name,d.specialty
        FROM appointments a JOIN users p ON p.id=a.patient_id JOIN users d ON d.id=a.doctor_id WHERE a.id=?""",
            (aid,),
        )
        .fetchone()
    )
    if not row:
        raise Problem("Appointment not found.", 404)
    user = require()
    if user["role"] != "admin" and row[user["role"] + "_id"] != user["id"]:
        raise Problem("You cannot access this appointment.", 403)
    return row


def audit(action, aid=None):
    db().execute(
        "INSERT INTO audit(actor_id,action,appointment_id,created_at) VALUES(?,?,?,?)",
        (g.user["id"] if getattr(g, "user", None) else None, action, aid, stamp()),
    )


def enqueue(key, recipient, subject, body):
    db().execute(
        "INSERT OR IGNORE INTO outbox(event_key,recipient,subject,body,created_at) VALUES(?,?,?,?,?)",
        (key, recipient, subject, body, stamp()),
    )


def notify(row, event, reason=""):
    recipient = (
        db()
        .execute("SELECT email FROM users WHERE id=?", (row["patient_id"],))
        .fetchone()["email"]
    )
    doc = (
        db()
        .execute("SELECT name FROM users WHERE id=?", (row["doctor_id"],))
        .fetchone()["name"]
    )
    enqueue(
        f"appointment:{row['id']}:{row['revision']}:{event}",
        recipient,
        f"Nowshera Family Clinic · Appointment {event}",
        f"Your appointment with {doc} on {row['start'].replace('T',' ')} (Pakistan time) is {event.lower()}.\n{reason}\n\nSign in to view your appointment.\n{current_app.config['BASE_URL']}\n\nNowshera Family Clinic",
    )


def cancel(row, reason):
    db().execute(
        "UPDATE appointments SET status='Cancelled',reason=? WHERE id=?",
        (reason, row["id"]),
    )
    notify(row, "Cancelled", reason)
    audit("Cancelled: " + reason, row["id"])


def run_rules():
    """Caller holds a write transaction. Event keys make repeated runs idempotent."""
    for row in (
        db()
        .execute(
            "SELECT * FROM appointments WHERE status='Pending' AND start<=?", (stamp(),)
        )
        .fetchall()
    ):
        cancel(row, "The request was not confirmed before its start time.")
    tomorrow = (now().date() + timedelta(days=1)).isoformat()
    for row in (
        db()
        .execute(
            "SELECT * FROM appointments WHERE status='Confirmed' AND substr(start,1,10)=?",
            (tomorrow,),
        )
        .fetchall()
    ):
        notify(row, "Reminder", "Your appointment is tomorrow. Please arrive on time.")
