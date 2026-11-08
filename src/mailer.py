"""Outbound email over SMTP (Gmail app password, Outlook, any STARTTLS/SSL server).

Configure in .env:
  SMTP_HOST=smtp.gmail.com  SMTP_PORT=587  SMTP_USER=you@gmail.com
  SMTP_PASSWORD=<app password>  SMTP_FROM=you@gmail.com (optional, defaults to SMTP_USER)
"""
import os
import re
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Optional

EMAIL_RE = re.compile(r"^[^@\s<>,;]+@[^@\s<>,;]+\.[A-Za-z]{2,}$")
SMTP_TIMEOUT = 20
SSL_PORT = 465


class MailError(Exception):
    """Email could not be sent; message is safe to show the user."""


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    sender: str

    @classmethod
    def from_env(cls) -> Optional["SmtpConfig"]:
        host, user, password = (os.getenv(k, "").strip() for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))
        if not (host and user and password):
            return None
        try:
            port = int(os.getenv("SMTP_PORT", "587"))
        except ValueError:
            port = 587
        return cls(host, port, user, password, os.getenv("SMTP_FROM", "").strip() or user)


def send_email(config: SmtpConfig, to: str, subject: str, body: str, reply_to: str = "") -> None:
    if not EMAIL_RE.match(to):
        raise MailError("Recipient email address looks invalid.")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.sender, to, " ".join(subject.split())
    if reply_to and EMAIL_RE.match(reply_to):
        msg["Reply-To"] = reply_to
    msg.set_content(body)
    ctx = ssl.create_default_context()
    try:
        if config.port == SSL_PORT:
            with smtplib.SMTP_SSL(config.host, config.port, timeout=SMTP_TIMEOUT, context=ctx) as s:
                s.login(config.user, config.password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(config.host, config.port, timeout=SMTP_TIMEOUT) as s:
                s.starttls(context=ctx)
                s.login(config.user, config.password)
                s.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise MailError("SMTP login failed. For Gmail, use an App Password, not your normal password.") from e
    except (smtplib.SMTPException, OSError) as e:
        raise MailError(f"Could not send email: {e.__class__.__name__}.") from e
