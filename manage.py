"""Local administration. Run `python manage.py --help`."""

import argparse
import secrets
import getpass
from pathlib import Path
from werkzeug.security import generate_password_hash
from app import create_app
from app.db import db
from app.domain import stamp
from app.automation import tick


def demo(app):
    with app.app_context():
        conn = db()
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM users").fetchone():
            conn.rollback()
            print(
                "Existing database kept. Your accounts and appointments are unchanged."
            )
            return
        pw = "Clinic-" + secrets.token_urlsafe(9)
        accounts = [
            ("Clinic Manager", "admin@clinic.test", "", "admin", ""),
            ("Dr. Ayesha Khan", "ayesha@clinic.test", "", "doctor", "Family Medicine"),
            ("Dr. Hamza Ali", "hamza@clinic.test", "", "doctor", "Cardiology"),
            ("Dr. Sana Ahmed", "sana@clinic.test", "", "doctor", "Pediatrics"),
            ("Hassan Zia", "patient@clinic.test", "03001234567", "patient", ""),
            ("Demo Patient Two", "patient2@clinic.test", "03007654321", "patient", ""),
        ]
        for name, address, phone, role, specialty in accounts:
            uid = conn.execute(
                "INSERT INTO users(name,email,phone,password,role,specialty,created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    name,
                    address,
                    phone,
                    generate_password_hash(pw),
                    role,
                    specialty,
                    stamp(),
                ),
            ).lastrowid
            if role == "doctor":
                for day in range(6):
                    conn.execute(
                        "INSERT INTO availability(doctor_id,weekday,start,end) VALUES(?,?,?,?)",
                        (uid, day, "09:00", "13:00"),
                    )
                    conn.execute(
                        "INSERT INTO availability(doctor_id,weekday,start,end) VALUES(?,?,?,?)",
                        (uid, day, "15:00", "18:00"),
                    )
        file = Path(app.config["INSTANCE_DIR"]) / "DEMO-LOGINS.txt"
        file.write_text(
            "LOCAL DEMONSTRATION ACCOUNTS ONLY\n\nPassword for all demo accounts: "
            + pw
            + "\n\n"
            + "\n".join(f"{a[3]}: {a[1]}" for a in accounts)
            + "\n\nDo not publish this file or use real patient data in the demo.\n"
        )
        file.chmod(0o600)
        conn.commit()
        print(
            "Demo accounts created. Open instance/DEMO-LOGINS.txt for your generated password."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["demo", "admin", "automations"])
    args = parser.parse_args()
    app = create_app()
    if args.command == "demo":
        demo(app)
    elif args.command == "automations":
        tick(app)
        print("Automation cycle complete.")
    else:
        from app.domain import email, password, text

        address = input("Admin email: ")
        name = input("Admin name: ")
        pw = getpass.getpass("Password (10+ characters): ")
        with app.app_context():
            address = email({"email": address})
            pw = password({"password": pw})
            name = text({"name": name}, "name", 100)
            db().execute(
                "INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,'admin',?)",
                (name, address, generate_password_hash(pw), stamp()),
            )
        print("Admin created.")
