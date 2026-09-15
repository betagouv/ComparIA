import asyncio
import logging
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from html import escape

from backend.config import settings

logger = logging.getLogger("languia")

_HEX_COLOR_PATTERN = re.compile(r"#[0-9A-Fa-f]{6}\Z")
_DEFAULT_PLATFORM_NAME = "Compar:IA"
_DEFAULT_PRIMARY_COLOR = "#6464F3"
_DEFAULT_SECONDARY_COLOR = "#FF9575"

_EMAIL_SHELL = """\
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: {canvas_color}; color: #161616; font-family: Marianne, Arial, Helvetica, sans-serif; font-size: 16px; line-height: 1.5;">
  <div style="display: none; max-height: 0; overflow: hidden; opacity: 0; color: transparent;">{preheader}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width: 100%; background-color: {canvas_color};">
    <tr>
      <td align="center" style="padding: 32px 16px;">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="width: 100%; max-width: 600px; background-color: #ffffff; border-top: 6px solid {secondary_color};">
          <tr>
            <td style="padding: 28px 32px 20px; border-bottom: 1px solid #dddddd;">
              <p style="margin: 0; color: {primary_color}; font-size: 24px; font-weight: 700; line-height: 1.2;">{platform_name}</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 32px;">
              {content}
            </td>
          </tr>
          <tr>
            <td style="padding: 20px 32px; background-color: #eeeeee; color: #666666; font-size: 13px;">
              <p style="margin: 0;">Message automatique envoyé par {platform_name}.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

_LOGIN_CONTENT = """\
<h1 style="margin: 0 0 20px; font-size: 28px; line-height: 1.25;">Votre code de connexion</h1>
<p style="margin: 0 0 20px;">Bonjour,</p>
<p style="margin: 0 0 24px;">Saisissez ce code sur {platform_name} pour terminer votre connexion&nbsp;:</p>
<p style="margin: 0 0 24px; padding: 18px 12px; background-color: {primary_color}; color: #ffffff; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 32px; font-weight: 700; letter-spacing: 8px; line-height: 1.2; text-align: center;">{code}</p>
<p style="margin: 0 0 12px;"><strong>Ce code expire dans 10&nbsp;minutes.</strong></p>
<p style="margin: 0; color: #666666; font-size: 14px;">Vous n’avez pas demandé ce code&nbsp;? Vous pouvez ignorer ce message. Ne transmettez jamais ce code à une autre personne.</p>
"""

_INVITE_CONTENT = """\
<h1 style="margin: 0 0 20px; font-size: 28px; line-height: 1.25;">Vous êtes invité·e sur {platform_name}</h1>
<p style="margin: 0 0 20px;">Bonjour,</p>
<p style="margin: 0 0 24px;">Une personne vous invite à rejoindre l’espace d’administration de {platform_name}.</p>
<p style="margin: 0 0 24px;">
  <a href="{link}" style="display: inline-block; padding: 12px 20px; background-color: {primary_color}; color: #ffffff; font-weight: 700; text-decoration: underline;">Accepter l’invitation</a>
</p>
<p style="margin: 0 0 12px;"><strong>Cette invitation expire dans 24&nbsp;heures.</strong></p>
<p style="margin: 0 0 8px; color: #666666; font-size: 14px;">Si le bouton ne fonctionne pas, copiez cette adresse dans votre navigateur&nbsp;:</p>
<p style="margin: 0 0 20px; overflow-wrap: anywhere; font-size: 14px;"><a href="{link}" style="color: {primary_color}; text-decoration: underline;">{link_text}</a></p>
<p style="margin: 0; color: #666666; font-size: 14px;">Vous n’attendiez pas cette invitation&nbsp;? Vous pouvez ignorer ce message.</p>
"""

_INACTIVITY_CONTENT = """\
<div lang="{lang}">
<h1 style="margin: 0 0 20px; font-size: 28px; line-height: 1.25;">{title}</h1>
<p style="margin: 0 0 20px;">{greeting}</p>
<p style="margin: 0 0 12px;">{unused_since}</p>
<p style="margin: 0 0 12px;"><strong>{deleted_on}</strong></p>
<p style="margin: 0;">{sign_in} <a href="{link}" style="color: {primary_color}; text-decoration: underline;">{link_text}</a></p>
</div>
"""

# One entry per locale the warning can be written in. An instance whose
# default locale is missing here gets the English one.
_INACTIVITY_TEXTS = {
    "fr": {
        "months": (
            "janvier",
            "février",
            "mars",
            "avril",
            "mai",
            "juin",
            "juillet",
            "août",
            "septembre",
            "octobre",
            "novembre",
            "décembre",
        ),
        "date": lambda d, m, y: f"{'1er' if d == 1 else d} {m} {y}",
        "subject": "Votre compte {platform_name} sera supprimé le {erasure}",
        "preheader": "Connectez-vous avant le {erasure} pour conserver votre compte {platform_name}.",
        "title": "Votre compte sera supprimé le {erasure}",
        "greeting": "Bonjour,",
        "unused_since": "Votre compte sur {platform_name} n’a pas été utilisé depuis le {last_seen}.",
        "deleted_on": "Il sera supprimé le {erasure}.",
        "sign_in": "Connectez-vous avant cette date pour le conserver\u00a0:",
    },
    "en": {
        "months": (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ),
        "date": lambda d, m, y: f"{d} {m} {y}",
        "subject": "Your {platform_name} account will be deleted on {erasure}",
        "preheader": "Sign in before {erasure} to keep your {platform_name} account.",
        "title": "Your account will be deleted on {erasure}",
        "greeting": "Hello,",
        "unused_since": "Your account on {platform_name} has not been used since {last_seen}.",
        "deleted_on": "It will be deleted on {erasure}.",
        "sign_in": "Sign in before then to keep it:",
    },
    "da": {
        "months": (
            "januar",
            "februar",
            "marts",
            "april",
            "maj",
            "juni",
            "juli",
            "august",
            "september",
            "oktober",
            "november",
            "december",
        ),
        "date": lambda d, m, y: f"{d}. {m} {y}",
        "subject": "Din {platform_name}-konto bliver slettet den {erasure}",
        "preheader": "Log ind før den {erasure} for at beholde din {platform_name}-konto.",
        "title": "Din konto bliver slettet den {erasure}",
        "greeting": "Hej,",
        "unused_since": "Din konto på {platform_name} har ikke været brugt siden den {last_seen}.",
        "deleted_on": "Den bliver slettet den {erasure}.",
        "sign_in": "Log ind inden da for at beholde den:",
    },
}


def _inactivity_texts(lang: str) -> tuple[str, dict]:
    if lang not in _INACTIVITY_TEXTS:
        lang = "en"
    return lang, _INACTIVITY_TEXTS[lang]


def _format_date(value: datetime, texts: dict) -> str:
    return texts["date"](value.day, texts["months"][value.month - 1], value.year)


async def send_login_code(
    to_email: str,
    code: str,
    platform_name: str = _DEFAULT_PLATFORM_NAME,
    primary_color: str = _DEFAULT_PRIMARY_COLOR,
    secondary_color: str = _DEFAULT_SECONDARY_COLOR,
) -> None:
    if not settings.SMTP_HOST:
        # The code signs someone in on its own, so it belongs in the logs only
        # when a developer is reading them in place of a mailbox.
        if settings.LANGUIA_DEBUG:
            logger.info(f"[AUTH] Login code for {to_email}: {code}")
        else:
            logger.error(f"[AUTH] SMTP is not configured, no code sent to {to_email}")
        return
    message = _build_login_message(
        code,
        platform_name=platform_name,
        primary_color=primary_color,
        secondary_color=secondary_color,
    )
    await asyncio.to_thread(_send_message, to_email, message)


async def send_invite_link(
    to_email: str,
    link: str,
    platform_name: str = _DEFAULT_PLATFORM_NAME,
    primary_color: str = _DEFAULT_PRIMARY_COLOR,
    secondary_color: str = _DEFAULT_SECONDARY_COLOR,
) -> None:
    if not settings.SMTP_HOST:
        # The link carries the invite token, which is a credential too.
        if settings.LANGUIA_DEBUG:
            logger.info(f"[AUTH] Invite link for {to_email}: {link}")
        else:
            logger.error(f"[AUTH] SMTP is not configured, no invite sent to {to_email}")
        return
    message = _build_invite_message(
        link,
        platform_name=platform_name,
        primary_color=primary_color,
        secondary_color=secondary_color,
    )
    await asyncio.to_thread(_send_message, to_email, message)


async def send_inactivity_warning(
    to_email: str,
    last_seen_at: datetime,
    erasure_at: datetime,
    lang: str = "fr",
    platform_name: str = _DEFAULT_PLATFORM_NAME,
    primary_color: str = _DEFAULT_PRIMARY_COLOR,
    secondary_color: str = _DEFAULT_SECONDARY_COLOR,
) -> bool:
    """Returns whether the warning went out, so the caller only records it then."""
    if not settings.SMTP_HOST:
        if settings.LANGUIA_DEBUG:
            logger.info(
                f"[AUTH] Inactivity warning for {to_email}: erasure on {erasure_at:%Y-%m-%d}"
            )
            return True
        logger.error(f"[AUTH] SMTP is not configured, no warning sent to {to_email}")
        return False
    message = _build_inactivity_message(
        last_seen_at,
        erasure_at,
        lang=lang,
        platform_name=platform_name,
        primary_color=primary_color,
        secondary_color=secondary_color,
    )
    await asyncio.to_thread(_send_message, to_email, message)
    return True


def _build_login_message(
    code: str,
    platform_name: str = _DEFAULT_PLATFORM_NAME,
    primary_color: str = _DEFAULT_PRIMARY_COLOR,
    secondary_color: str = _DEFAULT_SECONDARY_COLOR,
) -> EmailMessage:
    primary_color, secondary_color, canvas_color = _email_colors(
        primary_color, secondary_color
    )
    platform_name = _safe_platform_name(platform_name)
    safe_platform_name = escape(platform_name)
    safe_code = escape(code)
    html = _EMAIL_SHELL.format(
        title=f"Votre code de connexion — {safe_platform_name}",
        preheader=f"Votre code de connexion à {safe_platform_name} expire dans 10 minutes.",
        platform_name=safe_platform_name,
        primary_color=primary_color,
        secondary_color=secondary_color,
        canvas_color=canvas_color,
        content=_LOGIN_CONTENT.format(
            code=safe_code,
            platform_name=safe_platform_name,
            primary_color=primary_color,
        ),
    )
    text = (
        f"Votre code de connexion — {platform_name}\n\n"
        f"Votre code : {code}\n\n"
        "Ce code expire dans 10 minutes.\n"
        "Vous n’avez pas demandé ce code ? Ignorez ce message et ne transmettez "
        "jamais ce code à une autre personne."
    )
    return _build_message(f"Votre code de connexion — {platform_name}", text, html)


def _build_invite_message(
    link: str,
    platform_name: str = _DEFAULT_PLATFORM_NAME,
    primary_color: str = _DEFAULT_PRIMARY_COLOR,
    secondary_color: str = _DEFAULT_SECONDARY_COLOR,
) -> EmailMessage:
    primary_color, secondary_color, canvas_color = _email_colors(
        primary_color, secondary_color
    )
    platform_name = _safe_platform_name(platform_name)
    safe_platform_name = escape(platform_name)
    safe_link = escape(link, quote=True)
    html = _EMAIL_SHELL.format(
        title=f"Invitation à rejoindre {safe_platform_name}",
        preheader=f"Vous êtes invité·e à rejoindre l’espace d’administration de {safe_platform_name}.",
        platform_name=safe_platform_name,
        primary_color=primary_color,
        secondary_color=secondary_color,
        canvas_color=canvas_color,
        content=_INVITE_CONTENT.format(
            link=safe_link,
            link_text=escape(link),
            platform_name=safe_platform_name,
            primary_color=primary_color,
        ),
    )
    text = (
        f"Vous êtes invité·e sur {platform_name}\n\n"
        f"Une personne vous invite à rejoindre l’espace d’administration de {platform_name}.\n\n"
        f"Accepter l’invitation : {link}\n\n"
        "Cette invitation expire dans 24 heures.\n"
        "Vous n’attendiez pas cette invitation ? Ignorez ce message."
    )
    return _build_message(f"Vous êtes invité·e sur {platform_name}", text, html)


def _build_inactivity_message(
    last_seen_at: datetime,
    erasure_at: datetime,
    lang: str = "fr",
    platform_name: str = _DEFAULT_PLATFORM_NAME,
    primary_color: str = _DEFAULT_PRIMARY_COLOR,
    secondary_color: str = _DEFAULT_SECONDARY_COLOR,
) -> EmailMessage:
    primary_color, secondary_color, canvas_color = _email_colors(
        primary_color, secondary_color
    )
    platform_name = _safe_platform_name(platform_name)
    safe_platform_name = escape(platform_name)
    link = settings.COMPARIA_APP_URL
    lang, texts = _inactivity_texts(lang)
    dates = {
        "last_seen": _format_date(last_seen_at, texts),
        "erasure": _format_date(erasure_at, texts),
    }

    def phrase(key: str, name: str) -> str:
        return texts[key].format(platform_name=name, **dates)

    html = _EMAIL_SHELL.format(
        title=phrase("subject", safe_platform_name),
        preheader=phrase("preheader", safe_platform_name),
        platform_name=safe_platform_name,
        primary_color=primary_color,
        secondary_color=secondary_color,
        canvas_color=canvas_color,
        content=_INACTIVITY_CONTENT.format(
            lang=lang,
            title=phrase("title", safe_platform_name),
            greeting=texts["greeting"],
            unused_since=phrase("unused_since", safe_platform_name),
            deleted_on=phrase("deleted_on", safe_platform_name),
            sign_in=phrase("sign_in", safe_platform_name),
            primary_color=primary_color,
            link=escape(link, quote=True),
            link_text=escape(link),
        ),
    )
    text = (
        f"{phrase('unused_since', platform_name)} "
        f"{phrase('deleted_on', platform_name)} "
        f"{phrase('sign_in', platform_name)} {link}"
    )
    return _build_message(phrase("subject", platform_name), text, html)


def _email_colors(primary_color: str, secondary_color: str) -> tuple[str, str, str]:
    primary = _safe_color(primary_color, _DEFAULT_PRIMARY_COLOR)
    secondary = _safe_color(secondary_color, _DEFAULT_SECONDARY_COLOR)
    return primary, secondary, _tint(secondary, white_ratio=0.92)


def _safe_color(color: str, fallback: str) -> str:
    return color.upper() if _HEX_COLOR_PATTERN.fullmatch(color) else fallback


def _safe_platform_name(platform_name: str) -> str:
    return " ".join(platform_name.split()) or _DEFAULT_PLATFORM_NAME


def _tint(color: str, white_ratio: float) -> str:
    channels = [int(color[index : index + 2], 16) for index in (1, 3, 5)]
    tinted = [
        round(channel * (1 - white_ratio) + 255 * white_ratio) for channel in channels
    ]
    return "#" + "".join(f"{channel:02X}" for channel in tinted)


def _build_message(subject: str, text: str, html: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return message


def _send_message(to_email: str, message: EmailMessage) -> None:
    smtp_host = settings.SMTP_HOST
    if smtp_host is None:
        raise RuntimeError("SMTP host is required to send an email")

    message["To"] = to_email
    with smtplib.SMTP(smtp_host, settings.SMTP_PORT) as smtp:
        if settings.SMTP_STARTTLS:
            smtp.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message, from_addr=settings.EMAIL_FROM, to_addrs=[to_email])
