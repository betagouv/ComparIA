from backend.auth.email import _build_invite_message, _build_login_message


def _parts(message):
    return {
        part.get_content_type(): part.get_content()
        for part in message.walk()
        if not part.is_multipart()
    }


def test_login_message_has_plain_text_and_accessible_html():
    message = _build_login_message("123456")
    parts = _parts(message)

    assert message["Subject"] == "Votre code de connexion — Compar:IA"
    assert "123456" in parts["text/plain"]
    assert '<html lang="fr">' in parts["text/html"]
    assert "Ce code expire dans 10&nbsp;minutes" in parts["text/html"]
    assert 'role="presentation"' in parts["text/html"]


def test_login_message_escapes_code_in_html():
    html = _parts(_build_login_message("<123&456>"))["text/html"]

    assert "&lt;123&amp;456&gt;" in html
    assert "<123&456>" not in html


def test_invite_message_has_fallback_link_in_both_parts():
    link = "https://comparia.example/invite/example-token"
    parts = _parts(_build_invite_message(link))

    assert link in parts["text/plain"]
    assert parts["text/html"].count(link) == 3
    assert "Cette invitation expire dans 24&nbsp;heures" in parts["text/html"]


def test_invite_message_escapes_link_attributes():
    html = _parts(
        _build_invite_message('https://comparia.example/invite?value="unsafe"&next=1')
    )["text/html"]

    assert "&quot;unsafe&quot;&amp;next=1" in html
    assert 'value="unsafe"' not in html


def test_login_message_uses_configured_platform_colors():
    html = _parts(
        _build_login_message(
            "123456", primary_color="#123456", secondary_color="#ABCDEF"
        )
    )["text/html"]

    assert "background-color: #123456" in html
    assert "color: #123456" in html
    assert "border-top: 6px solid #ABCDEF" in html
    assert "background-color: #F8FBFE" in html


def test_invite_message_rejects_unsafe_custom_colors():
    html = _parts(
        _build_invite_message(
            "https://comparia.example/invite/example-token",
            primary_color="red; display: none",
            secondary_color="not-a-color",
        )
    )["text/html"]

    assert "red; display: none" not in html
    assert "not-a-color" not in html
    assert "background-color: #6464F3" in html
    assert "border-top: 6px solid #FF9575" in html


def test_messages_use_the_configured_platform_name_without_fixed_subtitle():
    platform_name = "Arène & Compagnie"
    login = _build_login_message("123456", platform_name=platform_name)
    invite = _build_invite_message(
        "https://comparia.example/invite/example-token", platform_name=platform_name
    )
    login_parts = _parts(login)
    invite_parts = _parts(invite)

    assert login["Subject"] == "Votre code de connexion — Arène & Compagnie"
    assert invite["Subject"] == "Vous êtes invité·e sur Arène & Compagnie"
    assert "Arène &amp; Compagnie" in login_parts["text/html"]
    assert "Arène &amp; Compagnie" in invite_parts["text/html"]
    assert platform_name in login_parts["text/plain"]
    assert platform_name in invite_parts["text/plain"]
    assert (
        "Comparez les modèles d’intelligence artificielle"
        not in login_parts["text/html"]
    )
    assert "service numérique de l’État" not in login_parts["text/html"]


def test_platform_name_cannot_inject_email_headers_or_html():
    message = _build_login_message(
        "123456", platform_name="Test\nBcc: attacker@example.test <script>"
    )
    html = _parts(message)["text/html"]

    assert "\n" not in str(message["Subject"])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
