import logging

import brevo
from brevo.transactional_emails.types.send_transac_email_request_sender import (
    SendTransacEmailRequestSender,
)
from brevo.transactional_emails.types.send_transac_email_request_to_item import (
    SendTransacEmailRequestToItem,
)

from backend.config import settings

logger = logging.getLogger("languia")


async def send_login_code(to_email: str, code: str) -> None:
    if not settings.BREVO_API_KEY or not settings.BREVO_LOGIN_CODE_TEMPLATE_ID:
        logger.info(f"[AUTH] Login code for {to_email}: {code}")
        return

    logger.info(f"[AUTH] Sending login code via Brevo from={settings.EMAIL_FROM} to={to_email}")
    try:
        client = brevo.AsyncBrevo(api_key=settings.BREVO_API_KEY)
        await client.transactional_emails.send_transac_email(
            to=[SendTransacEmailRequestToItem(email=to_email)],
            sender=SendTransacEmailRequestSender(
                email=settings.EMAIL_FROM,
                name=settings.EMAIL_FROM_NAME,
            ),
            template_id=settings.BREVO_LOGIN_CODE_TEMPLATE_ID,
            params={"code": code},
        )
        logger.info(f"[AUTH] Login code sent via Brevo to {to_email}")
    except Exception as e:
        logger.error(f"[AUTH] Brevo failed for {to_email}: {e}")
        raise
