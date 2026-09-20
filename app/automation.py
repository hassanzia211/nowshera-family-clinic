"""Durable email outbox and appointment maintenance. No notes enter emails."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from .db import db
from .domain import run_rules, stamp
from flask import current_app


def tick(app):
    with app.app_context():
        conn = db()
        try:
            conn.execute("BEGIN IMMEDIATE")
            run_rules()
            conn.commit()
            ids = [
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM outbox WHERE state='queued' ORDER BY id LIMIT 50"
                )
            ]
            for mid in ids:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT * FROM outbox WHERE id=? AND state='queued'", (mid,)
                ).fetchone()
                if not row:
                    conn.commit()
                    continue
                # A single worker owns the DB write lock until delivery finishes.
                msg = EmailMessage()
                msg["From"] = current_app.config["SMTP_FROM"]
                msg["To"] = row["recipient"]
                msg["Subject"] = row["subject"]
                msg["Message-ID"] = f"<clinic-outbox-{mid}@nowshera.local>"
                msg.set_content(row["body"])
                try:
                    mode = current_app.config["MAIL_MODE"]
                    if mode == "file":
                        folder = Path(current_app.config["INSTANCE_DIR"]) / "outbox"
                        folder.mkdir(parents=True, exist_ok=True)
                        temp = folder / f"{mid:06d}.tmp"
                        dest = folder / f"{mid:06d}.eml"
                        temp.write_bytes(msg.as_bytes())
                        temp.replace(dest)
                        readable = folder / f"{mid:06d}.txt"
                        readable.write_text(
                            f"To: {row['recipient']}\nSubject: {row['subject']}\n\n{row['body']}",
                            encoding="utf-8",
                        )
                        state = "saved-local"
                    elif mode == "smtp":
                        host = current_app.config["SMTP_HOST"]
                        port = current_app.config["SMTP_PORT"]
                        if not host:
                            raise ValueError("SMTP host missing")
                        if not current_app.config["SMTP_TLS"]:
                            raise ValueError("SMTP_TLS must be true")
                        with smtplib.SMTP(host, port, timeout=10) as smtp:
                            smtp.ehlo()
                            smtp.starttls(context=ssl.create_default_context())
                            smtp.ehlo()
                            if current_app.config["SMTP_USER"]:
                                smtp.login(
                                    current_app.config["SMTP_USER"],
                                    current_app.config["SMTP_PASSWORD"],
                                )
                            smtp.send_message(msg)
                        state = "sent"
                    else:
                        raise ValueError("Unsupported MAIL_MODE")
                    conn.execute(
                        "UPDATE outbox SET state=?,sent_at=?,attempts=attempts+1,error=? WHERE id=?",
                        (state, stamp(), "", mid),
                    )
                except Exception as error:
                    # Never persist provider error text that might contain credentials.
                    conn.execute(
                        "UPDATE outbox SET attempts=attempts+1,error=? WHERE id=?",
                        (type(error).__name__, mid),
                    )
                    logging.warning(
                        "Email %s remains queued (%s)", mid, type(error).__name__
                    )
                conn.commit()
        except Exception:
            conn.rollback()
            logging.exception("Automation cycle failed")
            raise


def loop(app, stop):
    while not stop.is_set():
        try:
            tick(app)
        except Exception:
            pass
        stop.wait(30)
