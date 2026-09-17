import asyncio
import logging
import re
import smtplib
from email.message import EmailMessage
from html import escape

from backend.config import settings
from backend.utils.locale import BASE_LOCALE, pick_locale

logger = logging.getLogger("languia")

_HEX_COLOR_PATTERN = re.compile(r"#[0-9A-Fa-f]{6}\Z")
_DEFAULT_PLATFORM_NAME = "Compar:IA"
_DEFAULT_PRIMARY_COLOR = "#6464F3"
_DEFAULT_SECONDARY_COLOR = "#FF9575"

_EMAIL_SHELL = """\
<!DOCTYPE html>
<html lang="{lang}">
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
              <p style="margin: 0;">{footer}</p>
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
<h1 style="margin: 0 0 20px; font-size: 28px; line-height: 1.25;">{title}</h1>
<p style="margin: 0 0 20px;">{greeting}</p>
<p style="margin: 0 0 24px;">{intro}</p>
<p style="margin: 0 0 24px; padding: 18px 12px; background-color: {primary_color}; color: #ffffff; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 32px; font-weight: 700; letter-spacing: 8px; line-height: 1.2; text-align: center;">{code}</p>
<p style="margin: 0 0 12px;"><strong>{expires}</strong></p>
<p style="margin: 0; color: #666666; font-size: 14px;">{ignore}</p>
"""

_INVITE_CONTENT = """\
<h1 style="margin: 0 0 20px; font-size: 28px; line-height: 1.25;">{title}</h1>
<p style="margin: 0 0 20px;">{greeting}</p>
<p style="margin: 0 0 24px;">{intro}</p>
<p style="margin: 0 0 24px;">
  <a href="{link}" style="display: inline-block; padding: 12px 20px; background-color: {primary_color}; color: #ffffff; font-weight: 700; text-decoration: underline;">{accept}</a>
</p>
<p style="margin: 0 0 12px;"><strong>{expires}</strong></p>
<p style="margin: 0 0 8px; color: #666666; font-size: 14px;">{fallback}</p>
<p style="margin: 0 0 20px; overflow-wrap: anywhere; font-size: 14px;"><a href="{link}" style="color: {primary_color}; text-decoration: underline;">{link_text}</a></p>
<p style="margin: 0; color: #666666; font-size: 14px;">{ignore}</p>
"""

# Wording per locale. `{platform_name}` is filled in later, already escaped
# for the HTML parts. The plain-text parts reuse the same sentences.
_COPY: dict[str, dict[str, str]] = {
    "fr": {
        "footer": "Message automatique envoyé par {platform_name}.",
        "greeting": "Bonjour,",
        "login_subject": "Votre code de connexion — {platform_name}",
        "login_preheader": (
            "Votre code de connexion à {platform_name} expire dans 10 minutes."
        ),
        "login_title": "Votre code de connexion",
        "login_intro": (
            "Saisissez ce code sur {platform_name} pour terminer votre connexion :"
        ),
        "login_code": "Votre code :",
        "login_expires": "Ce code expire dans 10 minutes.",
        "login_ignore": (
            "Vous n’avez pas demandé ce code ? Vous pouvez ignorer ce message. "
            "Ne transmettez jamais ce code à une autre personne."
        ),
        "invite_subject": "Vous êtes invité·e sur {platform_name}",
        "invite_preheader": (
            "Vous êtes invité·e à rejoindre l’espace d’administration de "
            "{platform_name}."
        ),
        "invite_title": "Vous êtes invité·e sur {platform_name}",
        "invite_intro": (
            "Une personne vous invite à rejoindre l’espace d’administration de "
            "{platform_name}."
        ),
        "invite_accept": "Accepter l’invitation",
        "invite_link": "Accepter l’invitation :",
        "invite_expires": "Cette invitation expire dans 24 heures.",
        "invite_fallback": (
            "Si le bouton ne fonctionne pas, copiez cette adresse dans votre "
            "navigateur :"
        ),
        "invite_ignore": (
            "Vous n’attendiez pas cette invitation ? Vous pouvez ignorer ce " "message."
        ),
    },
    "en": {
        "footer": "Automatic message sent by {platform_name}.",
        "greeting": "Hello,",
        "login_subject": "Your sign-in code — {platform_name}",
        "login_preheader": (
            "Your sign-in code for {platform_name} expires in 10 minutes."
        ),
        "login_title": "Your sign-in code",
        "login_intro": "Enter this code on {platform_name} to finish signing in:",
        "login_code": "Your code:",
        "login_expires": "This code expires in 10 minutes.",
        "login_ignore": (
            "Did not ask for this code? You can ignore this message. Never "
            "share this code with anyone."
        ),
        "invite_subject": "You are invited to {platform_name}",
        "invite_preheader": (
            "You are invited to join the administration area of {platform_name}."
        ),
        "invite_title": "You are invited to {platform_name}",
        "invite_intro": (
            "Someone is inviting you to join the administration area of "
            "{platform_name}."
        ),
        "invite_accept": "Accept the invitation",
        "invite_link": "Accept the invitation:",
        "invite_expires": "This invitation expires in 24 hours.",
        "invite_fallback": (
            "If the button does not work, copy this address into your browser:"
        ),
        "invite_ignore": (
            "Were you not expecting this invitation? You can ignore this message."
        ),
    },
    "da": {
        "footer": "Automatisk besked sendt af {platform_name}.",
        "greeting": "Hej,",
        "login_subject": "Din loginkode — {platform_name}",
        "login_preheader": "Din loginkode til {platform_name} udløber om 10 minutter.",
        "login_title": "Din loginkode",
        "login_intro": "Indtast denne kode på {platform_name} for at logge ind:",
        "login_code": "Din kode:",
        "login_expires": "Koden udløber om 10 minutter.",
        "login_ignore": (
            "Har du ikke bedt om denne kode? Så kan du se bort fra denne besked. "
            "Del aldrig koden med andre."
        ),
        "invite_subject": "Du er inviteret til {platform_name}",
        "invite_preheader": (
            "Du er inviteret til at blive administrator på {platform_name}."
        ),
        "invite_title": "Du er inviteret til {platform_name}",
        "invite_intro": (
            "Nogen inviterer dig til administrationsområdet på {platform_name}."
        ),
        "invite_accept": "Acceptér invitationen",
        "invite_link": "Acceptér invitationen:",
        "invite_expires": "Invitationen udløber om 24 timer.",
        "invite_fallback": (
            "Hvis knappen ikke virker, kan du kopiere denne adresse ind i din "
            "browser:"
        ),
        "invite_ignore": (
            "Ventede du ikke denne invitation? Så kan du se bort fra denne besked."
        ),
    },
}


_BREAKABLE_SPACE = re.compile(r"(\d) | (?=[:?!])")


def _no_break(text: str) -> str:
    """ "10 minutes" and French " :" should not split across lines in HTML."""
    return _BREAKABLE_SPACE.sub(lambda m: f"{m.group(1) or ''}&nbsp;", text)


def _copy(
    locale: str, platform_name: str, html: bool = False
) -> tuple[str, dict[str, str]]:
    """The wording for `locale`, with the platform name filled in."""
    picked = pick_locale(locale, _COPY)
    copy = {}
    for key, value in _COPY[picked].items():
        value = value.format(platform_name=platform_name)
        copy[key] = _no_break(value) if html else value
    return picked, copy


async def send_login_code(
    to_email: str,
    code: str,
    platform_name: str = _DEFAULT_PLATFORM_NAME,
    primary_color: str = _DEFAULT_PRIMARY_COLOR,
    secondary_color: str = _DEFAULT_SECONDARY_COLOR,
    locale: str = BASE_LOCALE,
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
        locale=locale,
    )
    await asyncio.to_thread(_send_message, to_email, message)


async def send_invite_link(
    to_email: str,
    link: str,
    platform_name: str = _DEFAULT_PLATFORM_NAME,
    primary_color: str = _DEFAULT_PRIMARY_COLOR,
    secondary_color: str = _DEFAULT_SECONDARY_COLOR,
    locale: str = BASE_LOCALE,
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
        locale=locale,
    )
    await asyncio.to_thread(_send_message, to_email, message)


def _build_login_message(
    code: str,
    platform_name: str = _DEFAULT_PLATFORM_NAME,
    primary_color: str = _DEFAULT_PRIMARY_COLOR,
    secondary_color: str = _DEFAULT_SECONDARY_COLOR,
    locale: str = BASE_LOCALE,
) -> EmailMessage:
    primary_color, secondary_color, canvas_color = _email_colors(
        primary_color, secondary_color
    )
    platform_name = _safe_platform_name(platform_name)
    safe_platform_name = escape(platform_name)
    safe_code = escape(code)
    lang, text_copy = _copy(locale, platform_name)
    _, html_copy = _copy(locale, safe_platform_name, html=True)
    html = _EMAIL_SHELL.format(
        lang=lang,
        title=html_copy["login_subject"],
        preheader=html_copy["login_preheader"],
        platform_name=safe_platform_name,
        primary_color=primary_color,
        secondary_color=secondary_color,
        canvas_color=canvas_color,
        footer=html_copy["footer"],
        content=_LOGIN_CONTENT.format(
            code=safe_code,
            primary_color=primary_color,
            title=html_copy["login_title"],
            greeting=html_copy["greeting"],
            intro=html_copy["login_intro"],
            expires=html_copy["login_expires"],
            ignore=html_copy["login_ignore"],
        ),
    )
    text = (
        f"{text_copy['login_subject']}\n\n"
        f"{text_copy['login_code']} {code}\n\n"
        f"{text_copy['login_expires']}\n"
        f"{text_copy['login_ignore']}"
    )
    return _build_message(text_copy["login_subject"], text, html)


def _build_invite_message(
    link: str,
    platform_name: str = _DEFAULT_PLATFORM_NAME,
    primary_color: str = _DEFAULT_PRIMARY_COLOR,
    secondary_color: str = _DEFAULT_SECONDARY_COLOR,
    locale: str = BASE_LOCALE,
) -> EmailMessage:
    primary_color, secondary_color, canvas_color = _email_colors(
        primary_color, secondary_color
    )
    platform_name = _safe_platform_name(platform_name)
    safe_platform_name = escape(platform_name)
    safe_link = escape(link, quote=True)
    lang, text_copy = _copy(locale, platform_name)
    _, html_copy = _copy(locale, safe_platform_name, html=True)
    html = _EMAIL_SHELL.format(
        lang=lang,
        title=html_copy["invite_subject"],
        preheader=html_copy["invite_preheader"],
        platform_name=safe_platform_name,
        primary_color=primary_color,
        secondary_color=secondary_color,
        canvas_color=canvas_color,
        footer=html_copy["footer"],
        content=_INVITE_CONTENT.format(
            link=safe_link,
            link_text=escape(link),
            primary_color=primary_color,
            title=html_copy["invite_title"],
            greeting=html_copy["greeting"],
            intro=html_copy["invite_intro"],
            accept=html_copy["invite_accept"],
            expires=html_copy["invite_expires"],
            fallback=html_copy["invite_fallback"],
            ignore=html_copy["invite_ignore"],
        ),
    )
    text = (
        f"{text_copy['invite_subject']}\n\n"
        f"{text_copy['invite_intro']}\n\n"
        f"{text_copy['invite_link']} {link}\n\n"
        f"{text_copy['invite_expires']}\n"
        f"{text_copy['invite_ignore']}"
    )
    return _build_message(text_copy["invite_subject"], text, html)


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
