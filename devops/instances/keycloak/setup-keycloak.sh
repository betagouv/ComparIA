#!/usr/bin/env bash
# Configure the local Keycloak dev instance (started by keycloak.compose.yml)
# for testing the OIDC auth method. Idempotent: re-running refreshes the
# client secret and the test user's password, and prints the values to use
# in /admin/authentification.
#
# Overridable via env:
#   KEYCLOAK_PORT, KEYCLOAK_ADMIN_USERNAME, KEYCLOAK_ADMIN_PASSWORD,
#   OIDC_TESTER_EMAIL, OIDC_TESTER_PASSWORD
set -euo pipefail

PORT="${KEYCLOAK_PORT:-8080}"
ADMIN_USER="${KEYCLOAK_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
TESTER_EMAIL="${OIDC_TESTER_EMAIL:-oidc-tester@example.com}"
TESTER_PASSWORD="${OIDC_TESTER_PASSWORD:-Test1234!}"
REALM="master"
CALLBACK_URI="http://localhost:8008/api/auth/oidc/callback"
BASE="http://localhost:${PORT}"

log() { printf '[keycloak] %s\n' "$*"; }

# --- wait for the realm ----------------------------------------------------
log "waiting for Keycloak to answer..."
for _ in $(seq 1 60); do
    if curl -sf -o /dev/null --max-time 2 "${BASE}/realms/${REALM}"; then
        break
    fi
    sleep 2
done
curl -sf -o /dev/null --max-time 2 "${BASE}/realms/${REALM}" || {
    echo "Keycloak did not become ready on ${BASE} (is 'make keycloak' / the compose stack running?)" >&2
    exit 1
}

# --- admin api helpers -----------------------------------------------------
TOKEN=$(curl -sf -X POST "${BASE}/realms/${REALM}/protocol/openid-connect/token" \
    --data-urlencode "username=${ADMIN_USER}" \
    --data-urlencode "password=${ADMIN_PASSWORD}" \
    -d 'grant_type=password&client_id=admin-cli' \
    | python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')

kc() { # kc METHOD PATH [JSON_BODY]
    local method="$1" path="$2" body="${3:-}"
    if [ -n "$body" ]; then
        curl -sf -X "$method" "${BASE}/admin/realms/${REALM}${path}" \
            -H "Authorization: Bearer ${TOKEN}" -H 'Content-Type: application/json' -d "$body"
    else
        curl -sf -X "$method" "${BASE}/admin/realms/${REALM}${path}" \
            -H "Authorization: Bearer ${TOKEN}"
    fi
}

# --- comparia client -------------------------------------------------------
CLIENT_ID_INTERNAL=$(kc GET '/clients?clientId=comparia' | python3 -c 'import sys, json
c = json.load(sys.stdin)
print(c[0]["id"] if c else "")')

if [ -n "$CLIENT_ID_INTERNAL" ]; then
    log "client 'comparia' already configured"
else
    kc POST /clients "$(printf '{
        "clientId": "comparia",
        "enabled": true,
        "protocol": "openid-connect",
        "publicClient": false,
        "standardFlowEnabled": true,
        "redirectUris": ["%s"],
        "webOrigins": ["http://localhost:5173", "http://localhost:8008"]
    }' "$CALLBACK_URI")" >/dev/null
    CLIENT_ID_INTERNAL=$(kc GET '/clients?clientId=comparia' \
        | python3 -c 'import sys, json; print(json.load(sys.stdin)[0]["id"])')
    log "client 'comparia' created"
fi

SECRET=$(kc GET "/clients/${CLIENT_ID_INTERNAL}/client-secret" \
    | python3 -c 'import sys, json; print(json.load(sys.stdin)["value"])')

# --- test user -------------------------------------------------------------
USER_INTERNAL=$(kc GET "/users?email=${TESTER_EMAIL}" | python3 -c 'import sys, json
u = json.load(sys.stdin)
print(u[0]["id"] if u else "")')

if [ -z "$USER_INTERNAL" ]; then
    kc POST /users "$(printf '{
        "username": "oidc-tester",
        "email": "%s",
        "emailVerified": true,
        "enabled": true
    }' "$TESTER_EMAIL")" >/dev/null
    USER_INTERNAL=$(kc GET "/users?email=${TESTER_EMAIL}" \
        | python3 -c 'import sys, json; print(json.load(sys.stdin)[0]["id"])')
    log "user '${TESTER_EMAIL}' created"
else
    log "user '${TESTER_EMAIL}' already exists, resetting password"
fi

kc PUT "/users/${USER_INTERNAL}/reset-password" "$(printf '{
    "type": "password",
    "value": "%s",
    "temporary": false
}' "$TESTER_PASSWORD")" >/dev/null

# --- summary ---------------------------------------------------------------
cat <<EOF

[keycloak] ready. Configure the instance at http://localhost:5173/admin/authentification with:
    issuer:        ${BASE}/realms/${REALM}
    client id:     comparia
    client secret: ${SECRET}
    scopes:        openid email
    redirect URI (informational): ${CALLBACK_URI}

Test user: ${TESTER_EMAIL} / ${TESTER_PASSWORD}
Keycloak admin console: ${BASE} (${ADMIN_USER}/${ADMIN_PASSWORD})
EOF
