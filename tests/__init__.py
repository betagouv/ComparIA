import os

# Ticket 01 made OIDC_ENCRYPTION_KEY a required setting with no auto-generated
# fallback. Set it before any test module imports `backend.config`, so the
# singleton `settings` is built with a key regardless of which suite runs first.
os.environ.setdefault("OIDC_ENCRYPTION_KEY", "aa" * 32)
