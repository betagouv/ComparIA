import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.config import settings

logger = logging.getLogger("languia")

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: arial, helvetica, sans-serif; color: #3b3f44; font-size: 16px; line-height: 1.5; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Bonjour,</p>
  <p>Voici votre code de connexion à ComparIA&nbsp;:</p>
  <p style="font-size: 32px; font-weight: bold; letter-spacing: 8px; text-align: center; padding: 20px 0;">{code}</p>
  <p>Ce code est valable 10&nbsp;minutes. Si vous n'avez pas demandé à vous connecter, ignorez cet email.</p>
  <p>L'équipe ComparIA</p>
</body>
</html>
"""


async def send_login_code(to_email: str, code: str) -> None:
    if not settings.SMTP_HOST:
        logger.info(f"[AUTH] Login code for {to_email}: {code}")
        return
    await asyncio.to_thread(_send_smtp, to_email, code)


def _send_smtp(to_email: str, code: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Votre code de connexion ComparIA"
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    msg["To"] = to_email
    msg.attach(MIMEText(_HTML_TEMPLATE.format(code=code), "html", "utf-8"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        if settings.SMTP_STARTTLS:
            smtp.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
