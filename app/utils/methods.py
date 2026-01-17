from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import smtplib

import time

from app.models.schema import MyResponse
from app.utils.constants import MAIL_SUBJECT
from app.utils.enums.ResponseStatus import ResponseStatus
from datetime import datetime, timezone
import jwt
import humanize
from app.utils.messages import OTP_SENT


def serialize_doc(doc):
    """Convert MongoDB ObjectId to string as `id` instead of `_id`"""
    return {"id": str(doc["_id"]), "title": doc["title"], "icon": doc["icon"]}


def is_invalid_field(field: str) -> bool:
    return not field or field.strip().lower() == "string"


def is_valid_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None


def convert_iso_date_to_humanize(date) -> str:
    # If it's already a datetime object
    if isinstance(date, datetime):
        dt = date
    else:
        # If it's a string, parse it
        if isinstance(date, str) and date.endswith("Z"):
            dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(date)

    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    return humanize.naturaltime(now - dt)


def create_success_response(status_code: int, message: str, **kwargs):
    return MyResponse(
        status=ResponseStatus.SUCCESS.value,
        status_code=status_code,
        message=message,
        **kwargs,
    )


def create_exception_response(status_code, message):
    return MyResponse(
        status=ResponseStatus.FAILURE.name,
        status_code=status_code,
        message=message,
    )


def token_expired_at(token: str):
    decoded = jwt.decode(token, options={"verify_signature": False})
    expiry_timestamp = decoded.get("exp")
    if expiry_timestamp:
        return datetime.fromtimestamp(expiry_timestamp, tz=timezone.utc)
    else:
        return None


def send_otp_email(saved_email_config, email, otp):
    server = None

    if saved_email_config is None:
        return ResponseStatus.FAILURE.name, 400, "Email configuration missing"

    smtp_server = saved_email_config["mail_smtp_host"]
    smtp_port = int(saved_email_config["mail_smtp_port"])
    sender_email = saved_email_config["mail_smtp_user"]
    receiver_email = email
    password = saved_email_config["mail_smtp_password"]
    use_tls = saved_email_config.get("use_tls", True)

    # Build email
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = MAIL_SUBJECT

    html = (
        saved_email_config["otp_email_template"]
        .replace("{{process_type}}", "login")
        .replace("{{one_time_password}}", str(otp))
    )

    message.attach(MIMEText(html, "html"))

    try:
        if smtp_port == 465 or not use_tls:
            # SSL mode
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # TLS mode
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()

        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

        return ResponseStatus.SUCCESS.name, 200, OTP_SENT.format(email=email)

    except Exception as e:
        return ResponseStatus.FAILURE.name, 400, str(e)

    finally:
        if server:
            server.quit()


def generate_unique_referral_code(length=8):
    import random
    import string
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

