import os

# OIDC_ENCRYPTION_KEY is a required setting (no auto-generated fallback, see
# ticket 01 / backend/auth/encryption.py). Set it before any test module
# imports `backend.config`, so the singleton `settings` is built with a key
# regardless of which suite is collected first.
os.environ.setdefault("OIDC_ENCRYPTION_KEY", "aa" * 32)
