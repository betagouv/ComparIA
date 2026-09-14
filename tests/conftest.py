import os

# The app refuses to start without an Altcha key outside debug, so that a
# deployment cannot silently run with a per-process one. Tests are not a
# deployment: give them a fixed key before anything imports backend.config.
os.environ.setdefault("ALTCHA_HMAC_KEY", "test-altcha-hmac-key")
# Same for the authenticator secret key: any valid Fernet key will do.
os.environ.setdefault(
    "AUTH_TOTP_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
)
