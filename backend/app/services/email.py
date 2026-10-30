import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings


def send_email_with_attachment(to: str, subject: str, body: str, attachment_path: str, filename: str) -> None:
    if not settings.smtp_host:
        raise RuntimeError("SMTP not configured (SMTP_HOST empty)")

    msg = MIMEMultipart()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)

    if settings.smtp_tls:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
        server.starttls()
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
    if settings.smtp_user:
        server.login(settings.smtp_user, settings.smtp_password)
    server.sendmail(settings.smtp_from, [to], msg.as_string())
    server.quit()
