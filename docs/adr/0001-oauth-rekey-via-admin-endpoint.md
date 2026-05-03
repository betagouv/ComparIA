# ADR 0001: OAuth rekey via admin endpoint

## Status
Accepted, 2026-05-03

## Context
Clarifeye rotates refresh_tokens on every refresh. Holding the original refresh_token in a Railway env var (CLARIFEYE_REFRESH_TOKEN) was fragile: as soon as Redis was wiped, the bootstrap re-seeded a revoked token and the next refresh fell back to the authorization_code flow, which fails on a headless server.

## Decision
Token state lives only in Redis (or FileTokenStorage in dev). To re-key a server, an operator runs `scripts/auth_setup.py` locally, which performs the browser auth flow and POSTs the fresh refresh_token to `POST /admin/tool-arena/oauth/seed`.

## Consequences
- Single source of truth for tokens.
- Re-keying is one command, no Railway env-var edit + redeploy.
- Operator must have ADMIN_STATUS_TOKEN. (Trade-off: gain safety, lose the ability to re-key without backend access.)
- A Redis distributed lock prevents multi-replica refresh races.
