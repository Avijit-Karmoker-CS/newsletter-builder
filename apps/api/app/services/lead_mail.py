from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import get_settings


class MailDeliveryError(RuntimeError):
    pass


def send_review_email(*, to: str, subject: str, body: str) -> None:
    """Send the review link through the configured email service."""
    if any(char in to for char in "\n\r"):
        raise MailDeliveryError("Invalid recipient")
    settings = get_settings()
    host = (settings.smtp_host or "").strip()
    if not host:
        raise MailDeliveryError(
            "Email is not configured on this server. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM."
        )
    sender = (settings.smtp_from or settings.smtp_user or "").strip()
    if not sender:
        raise MailDeliveryError("Set SMTP_FROM to the address reviews are sent from.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to
    message.set_content(body)

    try:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(host, settings.smtp_port, timeout=30) as smtp:
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(message)
            return
        with smtplib.SMTP(host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise MailDeliveryError(str(exc)[:300]) from exc
