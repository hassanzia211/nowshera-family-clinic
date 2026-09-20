"""Same-origin JSON API. Every mutation is protected by CSRF and a write transaction."""

import hashlib
import secrets
from datetime import timedelta
from flask import Blueprint, request, session, g, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from .db import db
from .domain import *

api = Blueprint("api", __name__, url_prefix="/api")


def data():
    value = request.get_json()
    if not isinstance(value, dict):
        raise Problem("Send a JSON object.")
    return value


def public_user(row):
    return {
        key: row[key]
        for key in ("id", "name", "email", "phone", "role", "specialty", "active")
    }


@api.get("/session")
def me():
    return {
        "user": public_user(g.user) if g.user else None,
        "csrf": session["csrf"],
        "today": now().date().isoformat(),
        "now": stamp(),
        "timezone": "Asia/Karachi",
        "mail_mode": current_app.config["MAIL_MODE"],
    }


@api.post("/register")
def register():
    d = data()
    name = text(d, "name", 100)
    address = email(d)
    phone = text(d, "phone", 30)
    pw = password(d)
    if not re.fullmatch(r"[+\d()\s-]{7,30}", phone):
        raise Problem("Enter a valid phone number.")
    uid = (
        db()
        .execute(
            "INSERT INTO users(name,email,phone,password,role,created_at) VALUES(?,?,?,?,'patient',?)",
            (name, address, phone, generate_password_hash(pw), stamp()),
        )
        .lastrowid
    )
    session.clear()
    session.update(uid=uid, csrf=secrets.token_urlsafe(32))
    session.permanent = True
    return {"ok": True}, 201


@api.post("/login")
def login():
    d = data()
    address = email(d)
    pw = text(d, "password", 128)
    key = hashlib.sha256(
        (address + "|" + (request.remote_addr or "")).encode()
    ).hexdigest()
    attempt = (
        db().execute("SELECT * FROM login_attempts WHERE key=?", (key,)).fetchone()
    )
    if (
        attempt
        and attempt["window"]
        > (now() - timedelta(minutes=15)).isoformat(timespec="seconds")
        and attempt["count"] >= 10
    ):
        raise Problem("Too many attempts. Try again in 15 minutes.", 429)
    user = (
        db()
        .execute("SELECT * FROM users WHERE email=? AND active=1", (address,))
        .fetchone()
    )
    if (
        not user
        or not user["password"]
        or not check_password_hash(user["password"], pw)
    ):
        count = (
            attempt["count"] + 1
            if attempt
            and attempt["window"]
            > (now() - timedelta(minutes=15)).isoformat(timespec="seconds")
            else 1
        )
        db().execute(
            "INSERT OR REPLACE INTO login_attempts VALUES(?,?,?)", (key, count, stamp())
        )
        db().commit()  # Preserve throttling for this intentionally unsuccessful request.
        raise Problem("Incorrect email or password.", 401)
    db().execute("DELETE FROM login_attempts WHERE key=?", (key,))
    session.clear()
    session.update(uid=user["id"], csrf=secrets.token_urlsafe(32))
    session.permanent = True
    return {"ok": True}


@api.post("/logout")
def logout():
    session.clear()
    return {"ok": True}


@api.post("/set-password")
def set_password():
    d = data()
    token = text(d, "token", 200)
    pw = password(d)
    hashed = hashlib.sha256(token.encode()).hexdigest()
    invitation = (
        db()
        .execute(
            "SELECT * FROM invitations WHERE token_hash=? AND used=0 AND expires>?",
            (hashed, stamp()),
        )
        .fetchone()
    )
    if not invitation:
        raise Problem(
            "This invitation has expired or was already used. Ask the admin for a new invitation."
        )
    db().execute(
        "UPDATE users SET password=? WHERE id=?",
        (generate_password_hash(pw), invitation["user_id"]),
    )
    db().execute(
        "UPDATE invitations SET used=1 WHERE user_id=?", (invitation["user_id"],)
    )
    return {"ok": True}


def invite(uid, address):
    token = secrets.token_urlsafe(32)
    db().execute("UPDATE invitations SET used=1 WHERE user_id=?", (uid,))
    db().execute(
        "INSERT INTO invitations VALUES(?,?,?,0)",
        (
            hashlib.sha256(token.encode()).hexdigest(),
            uid,
            (now() + timedelta(hours=24)).isoformat(timespec="seconds"),
        ),
    )
    enqueue(
        "invite:" + secrets.token_hex(16),
        address,
        "Set your Nowshera Family Clinic password",
        "Welcome to Nowshera Family Clinic. Set your password using this single-use link (valid for 24 hours):\n"
        + current_app.config["BASE_URL"]
        + "/#invite="
        + token,
    )


@api.get("/doctors")
def doctors():
    user = require()
    query = "SELECT id,name,email,specialty,active FROM users WHERE role='doctor'"
    if user["role"] != "admin":
        query += " AND active=1"
    return {"doctors": [dict(r) for r in db().execute(query + " ORDER BY name")]}


@api.post("/doctors")
def add_doctor():
    require("admin")
    d = data()
    address = email(d)
    uid = (
        db()
        .execute(
            "INSERT INTO users(name,email,specialty,role,created_at) VALUES(?,?,?,'doctor',?)",
            (text(d, "name", 100), address, text(d, "specialty", 100), stamp()),
        )
        .lastrowid
    )
    invite(uid, address)
    audit("Doctor invited")
    return {"id": uid, "message": "Doctor created. Password invitation queued."}, 201


@api.post("/doctors/<int:uid>/invite")
def resend_invite(uid):
    require("admin")
    doc = doctor(uid, True)
    if (
        db()
        .execute("SELECT password FROM users WHERE id=?", (uid,))
        .fetchone()["password"]
    ):
        raise Problem("This doctor has already set a password.")
    invite(uid, doc["email"])
    return {"ok": True}


@api.patch("/doctors/<int:uid>")
def toggle_doctor(uid):
    require("admin")
    doctor(uid)
    d = data()
    if type(d.get("active")) is not bool:
        raise Problem("Active must be true or false.")
    db().execute("UPDATE users SET active=? WHERE id=?", (int(d["active"]), uid))
    if not d["active"]:
        for row in (
            db()
            .execute(
                "SELECT * FROM appointments WHERE doctor_id=? AND status IN ('Pending','Confirmed') AND start>?",
                (uid, stamp()),
            )
            .fetchall()
        ):
            cancel(row, "The doctor is no longer available at the clinic.")
    audit("Doctor activated" if d["active"] else "Doctor deactivated")
    return {"ok": True}


@api.get("/doctors/<int:uid>/slots")
def slots(uid):
    user = require("patient", "admin")
    doctor(uid, True)
    day = parse_date(request.args.get("date", ""))
    available = []
    if day >= now().date():
        for window in db().execute(
            "SELECT * FROM availability WHERE doctor_id=? AND weekday=? ORDER BY start",
            (uid, day.weekday()),
        ):
            start = parse_start(day.isoformat() + "T" + window["start"])
            end = parse_start(day.isoformat() + "T" + window["end"])
            while start + timedelta(minutes=30) <= end:
                try:
                    validate_slot(uid, user["id"], start)
                    available.append(start.isoformat(timespec="seconds"))
                except Problem:
                    pass
                start += timedelta(minutes=30)
    return {"slots": available}


@api.get("/availability")
def availability():
    user = require("doctor")
    return {
        "hours": [
            dict(r)
            for r in db().execute(
                "SELECT * FROM availability WHERE doctor_id=? ORDER BY weekday,start",
                (user["id"],),
            )
        ],
        "leaves": [
            dict(r)
            for r in db().execute(
                "SELECT * FROM leaves WHERE doctor_id=? AND date>=? ORDER BY date",
                (user["id"], now().date().isoformat()),
            )
        ],
    }


@api.post("/availability")
def add_hours():
    user = require("doctor")
    d = data()
    weekday = d.get("weekday")
    start = d.get("start")
    end = d.get("end")
    if type(weekday) is not int or weekday not in range(7):
        raise Problem("Choose a valid weekday.")
    if (
        not all(
            isinstance(t, str) and re.fullmatch(r"(?:[01]\d|2[0-3]):(?:00|30)", t)
            for t in (start, end)
        )
        or start >= end
    ):
        raise Problem("Hours must end after they start and use 30-minute boundaries.")
    if (
        db()
        .execute(
            "SELECT 1 FROM availability WHERE doctor_id=? AND weekday=? AND start<? AND end>?",
            (user["id"], weekday, end, start),
        )
        .fetchone()
    ):
        raise Problem("These hours overlap an existing working period.", 409)
    db().execute(
        "INSERT INTO availability(doctor_id,weekday,start,end) VALUES(?,?,?,?)",
        (user["id"], weekday, start, end),
    )
    return {"ok": True}, 201


@api.delete("/availability/<int:wid>")
def delete_hours(wid):
    user = require("doctor")
    window = (
        db()
        .execute(
            "SELECT * FROM availability WHERE id=? AND doctor_id=?", (wid, user["id"])
        )
        .fetchone()
    )
    if not window:
        raise Problem("Working period not found.", 404)
    for row in db().execute(
        "SELECT start FROM appointments WHERE doctor_id=? AND status IN ('Pending','Confirmed') AND start>?",
        (user["id"], stamp()),
    ):
        start = parse_start(row["start"])
        if (
            start.weekday() == window["weekday"]
            and window["start"] <= start.strftime("%H:%M") < window["end"]
        ):
            raise Problem(
                "This period contains future appointments. Cancel them first or add a leave day.",
                409,
            )
    db().execute("DELETE FROM availability WHERE id=?", (wid,))
    return {"ok": True}


@api.post("/leaves")
def leave():
    user = require("doctor")
    day = parse_date(data().get("date"))
    if day < now().date():
        raise Problem("A leave day cannot be in the past.")
    db().execute(
        "INSERT INTO leaves(doctor_id,date) VALUES(?,?)", (user["id"], day.isoformat())
    )
    rows = (
        db()
        .execute(
            "SELECT * FROM appointments WHERE doctor_id=? AND substr(start,1,10)=? AND status IN ('Pending','Confirmed')",
            (user["id"], day.isoformat()),
        )
        .fetchall()
    )
    for row in rows:
        cancel(row, "The doctor is on leave on this date.")
    return {"ok": True, "cancelled": len(rows)}, 201


@api.delete("/leaves/<int:lid>")
def delete_leave(lid):
    user = require("doctor")
    if (
        not db()
        .execute("DELETE FROM leaves WHERE id=? AND doctor_id=?", (lid, user["id"]))
        .rowcount
    ):
        raise Problem("Leave day not found.", 404)
    return {"ok": True}


@api.get("/appointments")
def appointments():
    user = require()
    where = []
    args = []
    if user["role"] != "admin":
        where.append("a." + user["role"] + "_id=?")
        args.append(user["id"])
    for field, column in [
        ("doctor", "a.doctor_id"),
        ("date", "substr(a.start,1,10)"),
        ("status", "a.status"),
    ]:
        value = request.args.get(field)
        if value:
            where.append(column + "=?")
            args.append(value)
    query = """SELECT a.*,p.name patient_name,p.email patient_email,p.phone patient_phone,d.name doctor_name,d.specialty
        FROM appointments a JOIN users p ON p.id=a.patient_id JOIN users d ON d.id=a.doctor_id"""
    if where:
        query += " WHERE " + " AND ".join(where)
    return {
        "appointments": [
            dict(r)
            for r in db().execute(query + " ORDER BY a.start DESC,a.id DESC", args)
        ]
    }


@api.post("/appointments")
def book():
    user = require("patient")
    d = data()
    uid = d.get("doctor_id")
    if type(uid) is not int:
        raise Problem("Choose a doctor.")
    start = parse_start(d.get("start"))
    validate_slot(uid, user["id"], start)
    aid = (
        db()
        .execute(
            "INSERT INTO appointments(patient_id,doctor_id,start,status,created_at) VALUES(?,?,?,'Pending',?)",
            (user["id"], uid, start.isoformat(timespec="seconds"), stamp()),
        )
        .lastrowid
    )
    audit("Appointment requested", aid)
    return {"id": aid, "status": "Pending"}, 201


@api.get("/appointments/<int:aid>")
def detail(aid):
    return {"appointment": dict(appointment(aid))}


@api.post("/appointments/<int:aid>/reschedule")
def reschedule(aid):
    require("patient")
    row = appointment(aid)
    if row["status"] not in ACTIVE:
        raise Problem("Only Pending or Confirmed appointments can be rescheduled.")
    if parse_start(row["start"]) - now() < timedelta(hours=2):
        raise Problem("You must reschedule at least 2 hours before the appointment.")
    start = parse_start(data().get("start"))
    if start == parse_start(row["start"]):
        raise Problem("Choose a different slot.")
    validate_slot(row["doctor_id"], row["patient_id"], start, aid)
    db().execute(
        "UPDATE appointments SET start=?,status='Pending',reason='',revision=revision+1 WHERE id=?",
        (start.isoformat(timespec="seconds"), aid),
    )
    audit("Rescheduled", aid)
    return {"ok": True, "status": "Pending"}


@api.post("/appointments/<int:aid>/status")
def status(aid):
    user = require()
    row = appointment(aid)
    d = data()
    target = d.get("status")
    if target == "Cancelled":
        if user["role"] not in ("patient", "admin"):
            raise Problem("Doctors can reject requests or mark leave days.", 403)
        if row["status"] not in ACTIVE:
            raise Problem("This appointment is already closed.")
        if user["role"] == "patient" and parse_start(row["start"]) - now() < timedelta(
            hours=2
        ):
            raise Problem("You must cancel at least 2 hours before the appointment.")
        cancel(row, "Cancelled by the " + user["role"] + ".")
    else:
        require("doctor")
        if target in ("Confirmed", "Rejected"):
            if row["status"] != "Pending":
                raise Problem("Only Pending requests can be confirmed or rejected.")
            if parse_start(row["start"]) <= now():
                raise Problem(
                    "This request has expired and cannot be confirmed or rejected."
                )
        elif target in ("Completed", "No-show"):
            if row["status"] != "Confirmed":
                raise Problem(
                    "Only Confirmed appointments can be completed or marked No-show."
                )
            if parse_start(row["start"]) > now():
                raise Problem("The appointment has not started yet.")
        else:
            raise Problem("Choose a valid appointment status.")
        db().execute("UPDATE appointments SET status=? WHERE id=?", (target, aid))
        if target in ("Confirmed", "Rejected"):
            notify(row, target)
        if target in ("Completed", "No-show") and "note" in d:
            db().execute(
                "INSERT OR REPLACE INTO notes VALUES(?,?)",
                (aid, text(d, "note", 2000, False)),
            )
        audit(target, aid)
    return {"ok": True}


@api.get("/appointments/<int:aid>/note")
def read_note(aid):
    require("doctor", "patient")
    appointment(aid)
    row = (
        db().execute("SELECT body FROM notes WHERE appointment_id=?", (aid,)).fetchone()
    )
    return {"note": row["body"] if row else ""}


@api.put("/appointments/<int:aid>/note")
def save_note(aid):
    require("doctor")
    row = appointment(aid)
    if row["status"] not in ("Completed", "No-show"):
        raise Problem("Finish the visit before adding a note.")
    db().execute(
        "INSERT OR REPLACE INTO notes VALUES(?,?)",
        (aid, text(data(), "note", 2000, False)),
    )
    return {"ok": True}


@api.get("/patients")
def patients():
    user = require("admin", "doctor")
    q = request.args.get("q", "")[:100]
    sql = "SELECT id,name,email,phone FROM users WHERE role='patient' AND (name LIKE ? OR email LIKE ? OR phone LIKE ?)"
    args = ["%" + q + "%"] * 3
    if user["role"] == "doctor":
        sql += " AND id IN (SELECT patient_id FROM appointments WHERE doctor_id=?)"
        args.append(user["id"])
    return {"patients": [dict(r) for r in db().execute(sql + " ORDER BY name", args)]}


@api.get("/patients/<int:pid>/history")
def history(pid):
    user = require("doctor")
    rows = (
        db()
        .execute(
            """SELECT a.id,a.start,a.status,n.body note FROM appointments a LEFT JOIN notes n ON n.appointment_id=a.id
        WHERE a.patient_id=? AND a.doctor_id=? ORDER BY a.start DESC""",
            (pid, user["id"]),
        )
        .fetchall()
    )
    if not rows:
        raise Problem("You cannot access this patient history.", 403)
    return {"history": [dict(r) for r in rows]}


@api.get("/dashboard")
def dashboard():
    user = require()
    where = ""
    args = []
    if user["role"] != "admin":
        where = " WHERE " + user["role"] + "_id=?"
        args = [user["id"]]
    counts = {s: 0 for s in STATUSES}
    for r in db().execute(
        "SELECT status,count(*) total FROM appointments" + where + " GROUP BY status",
        args,
    ):
        counts[r["status"]] = r["total"]
    today = (
        db()
        .execute(
            "SELECT count(*) FROM appointments"
            + where
            + (" AND " if where else " WHERE ")
            + "substr(start,1,10)=?",
            args + [now().date().isoformat()],
        )
        .fetchone()[0]
    )
    result = {"counts": counts, "today": today}
    if user["role"] == "admin":
        doctors = []
        for doc in (
            db()
            .execute(
                "SELECT id,name,specialty,active FROM users WHERE role='doctor' ORDER BY name"
            )
            .fetchall()
        ):
            dc = {s: 0 for s in STATUSES}
            for r in db().execute(
                "SELECT status,count(*) total FROM appointments WHERE doctor_id=? GROUP BY status",
                (doc["id"],),
            ):
                dc[r["status"]] = r["total"]
            doctors.append({**dict(doc), "counts": dc})
        result["doctors"] = doctors
        result["patients"] = (
            db()
            .execute("SELECT count(*) FROM users WHERE role='patient'")
            .fetchone()[0]
        )
        result["mail"] = [
            dict(r)
            for r in db().execute(
                "SELECT state,count(*) total FROM outbox GROUP BY state"
            )
        ]
    return result
