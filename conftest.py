import os

# `backend.config.settings` is built once, by whichever test module imports it
# first. Give it an encryption key up front so the suites that store an OIDC
# client secret work whatever the collection order.
os.environ.setdefault("OIDC_ENCRYPTION_KEY", "aa" * 32)
