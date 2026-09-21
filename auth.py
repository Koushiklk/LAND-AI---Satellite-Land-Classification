"""
LAND AI - Authentication & 2-step verification
------------------------------------------------
Flow implemented here:

  Register (username + email + password)
        -> account created (unverified)
        -> OTP generated + "sent"
        -> user enters OTP -> account verified -> logged in

  Login (username/email + password)
        -> credentials checked
        -> OTP generated + "sent"        <-- this is the 2nd step
        -> user enters OTP -> logged in

In DEV_MODE (see config.py) the OTP is not actually emailed - it is
returned to the template and printed to the console, so you can test
the whole flow without setting up SMTP. Flip DEV_MODE off and fill in
SMTP_* in config.py to send real emails.
"""

import random
import smtplib
import string
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from database import get_db


# ---------- passwords ----------

def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


# ---------- OTP ----------

def generate_otp_code() -> str:
    return "".join(random.choices(string.digits, k=Config.OTP_LENGTH))


def create_otp(user_id: int, purpose: str) -> str:
    """Create + store a fresh OTP for a user, invalidating older unused ones."""
    code = generate_otp_code()
    expires_at = (datetime.utcnow() + timedelta(minutes=Config.OTP_EXPIRY_MINUTES)).isoformat()

    conn = get_db()
    cur = conn.cursor()
    # invalidate previous unused codes for this purpose
    cur.execute(
        "UPDATE otp_codes SET used = 1 WHERE user_id = ? AND purpose = ? AND used = 0",
        (user_id, purpose),
    )
    cur.execute(
        "INSERT INTO otp_codes (user_id, code, purpose, expires_at) VALUES (?, ?, ?, ?)",
        (user_id, code, purpose, expires_at),
    )
    conn.commit()
    conn.close()
    return code


def verify_otp(user_id: int, purpose: str, code: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM otp_codes
           WHERE user_id = ? AND purpose = ? AND code = ? AND used = 0
           ORDER BY id DESC LIMIT 1""",
        (user_id, purpose, code),
    )
    row = cur.fetchone()

    if row is None:
        conn.close()
        return False

    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        conn.close()
        return False

    cur.execute("UPDATE otp_codes SET used = 1 WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    return True


def send_otp_email(to_email: str, code: str) -> None:
    """
    Sends the OTP by email. In DEV_MODE this just prints to the console
    (the OTP is also shown on-screen by the route, for easy local testing).
    """
    subject = "Your LAND AI verification code"
    body = f"Your LAND AI verification code is: {code}\nIt expires in {Config.OTP_EXPIRY_MINUTES} minutes."

    if Config.DEV_MODE or not Config.SMTP_USERNAME:
        print(f"[DEV MODE] OTP for {to_email}: {code}")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = Config.SMTP_FROM
    msg["To"] = to_email

    with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
        server.starttls()
        server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        server.sendmail(Config.SMTP_FROM, [to_email], msg.as_string())
