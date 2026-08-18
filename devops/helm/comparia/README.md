# comparia Helm chart

Installs ComparIA (backend + frontend) on a Kubernetes cluster. This is the
Kubernetes-native alternative to the single-machine Docker Compose setup at
[`devops/standalone_docker_install/DOCKER_INSTALL.md`](../standalone_docker_install/DOCKER_INSTALL.md);
if you only need one server behind Caddy, that path is simpler.

The chart deploys:

- separate backend and frontend Deployments/Services
- a `Secret` (chart-rendered from values, or a pre-existing one you point it
  at) carrying API keys and DB/Redis connection info
- a pre-install/pre-upgrade Job that runs the app's Alembic migrations
- three optional CronJobs (ranking computation, dataset export, LLM-based
  analysis)
- an optional Ingress

It does not include a Postgres or Redis instance, an S3 log-archival sidecar,
or any blue-green deployment mechanism. Bring your own Postgres and Redis;
point the chart at them via `secrets.dbUri` / `secrets.redisHost`.

## Install

```bash
helm install comparia devops/helm/comparia \
  --set secrets.dbUri=postgresql://user:pass@host:5432/comparia \
  --set secrets.redisHost=redis.example.svc.cluster.local \
  --set secrets.altchaHmacKey=$(openssl rand -hex 32) \
  --set secrets.openrouterApiKey=sk-or-...
```

`helm install`/`helm template` fails with a named error if a required value
is missing: `secrets.dbUri`, `secrets.redisHost`, `secrets.altchaHmacKey`, and
at least one LLM provider key, unless `secrets.existingSecret` is set (see
[Secrets](#secrets) below).

## Values

### Images

| Value                    | Default                             | Description                                       |
| ------------------------ | ------------------------------------ | -------------------------------------------------- |
| `image.backend.repository` | `ghcr.io/betagouv/comparia-backend` | Backend image                                     |
| `image.backend.tag`        | `.Chart.AppVersion`                 | Backend image tag, independent of the chart version |
| `image.frontend.repository` | `ghcr.io/betagouv/comparia-frontend` | Frontend image                                   |
| `image.frontend.tag`       | `.Chart.AppVersion`                 | Frontend image tag, independent of the chart version |
| `image.pullPolicy`         | `IfNotPresent`                      | Applied to every container                        |
| `image.pullSecrets`        | `[]`                                 | List of `imagePullSecrets` names                  |

### Workloads

| Value                    | Default | Description                          |
| ------------------------- | ------- | ------------------------------------- |
| `replicaCount.backend`    | `1`     | Backend replica count                 |
| `replicaCount.frontend`   | `1`     | Frontend replica count                |
| `service.backend.port`    | `80`    | Backend Service port                  |
| `service.frontend.port`   | `80`    | Frontend Service port                 |
| `resources.backend`       | see `values.yaml` | Backend requests/limits    |
| `resources.frontend`      | see `values.yaml` | Frontend requests/limits   |
| `resources.migration`     | see `values.yaml` | Migration Job requests/limits |
| `resources.cronjobs`      | see `values.yaml` | Applied to all three CronJobs |
| `backend.extraEnv`        | `[]`    | Extra env vars for the backend container, for anything not covered by `config.*`/`secrets.*` below, same shape as a container's `env:` list |
| `frontend.extraEnv`       | `[]`    | Extra env vars for the frontend container, same shape |
| `frontend.publicApiUrl`   | `""`    | Public URL the frontend is served at; empty means same-origin |
| `frontend.disabledLocales`| `""`    | Comma-separated locales to hide from the language switcher |

### Non-secret app config (`config.*`)

| Value                     | Default            | Description                                          |
| -------------------------- | ------------------- | ----------------------------------------------------- |
| `config.instanceName`      | `fr`                | Redis key namespace / default locale. Also the name used the one time the migration hook seeds a HuggingFace destination — see [Dataset export](#dataset-export) |
| `config.authAccessPolicy`  | `anonymous_first`   | `anonymous_first` or `sign_in_required`               |
| `config.logFormat`         | `JSON`              | `JSON` or `RAW`                                       |
| `config.votesObjective`    | `300000`            | Displayed vote-count target                           |
| `config.cache.enabled`     | `true`              | LLM response cache                                    |
| `config.cache.probability` | `0.75`              | Probability of serving a cached response on hit       |
| `config.cache.ttl`         | `172800`            | Cache TTL in seconds                                  |
| `config.cache.maxResponses`| `5`                 | Max cached responses per (model, prompt) pair         |
| `config.sentryDsn`         | `""`                | Left empty, errors are not sent anywhere              |
| `config.sentryEnvironment` | `prod`              |                                                        |
| `config.appUrl`            | `""`                | `COMPARIA_APP_URL`, public origin used to build absolute links in emails (login codes). Left empty, falls back to the app's own dev default — set this for a real install |
| `config.adminEmails`       | `[]`                | `ADMIN_EMAILS`, promoted to the admin role on startup, created if absent. Left empty, nobody can reach `/admin` |
| `config.auth.domainAllowlist` | `[]`             | `AUTH_DOMAIN_ALLOWLIST`. If non-empty, only emails from these domains can request a login code |
| `config.auth.sessionLengthDays` | `30`           | `AUTH_SESSION_LENGTH_DAYS`                            |
| `config.currency.display`  | `EUR`               | `DISPLAY_CURRENCY`, ISO 4217 code models prices are converted to for display |
| `config.currency.rateFromEur` | `null`            | `DISPLAY_CURRENCY_RATE_FROM_EUR`, manual EUR conversion rate. Set to enable a currency unavailable from the rate API, run fully offline, or avoid the EUR fallback if the rate service is unreachable at startup |
| `config.currency.exchangeApiUrl` | `https://api.frankfurter.dev/v2` | `EXCHANGE_RATE_API_URL`                |
| `config.currency.exchangeCacheSeconds` | `86400`  | `EXCHANGE_RATE_CACHE_SECONDS`                         |
| `config.emailFrom`         | `""`                | `EMAIL_FROM`. Left empty, falls back to the app's own default |
| `config.emailFromName`     | `ComparIA`          | `EMAIL_FROM_NAME`                                     |
| `config.smtp.host`         | `""`                | `SMTP_HOST`. Left empty, login codes are logged to console instead of being sent by email |
| `config.smtp.port`         | `587`               | `SMTP_PORT`. Only rendered when `config.smtp.host` is set |

### Secrets

`secrets.existingSecret`, when set, takes precedence: the chart points every
workload's `envFrom` at that Secret and renders no `Secret` of its own. Use
this if you manage secrets externally (Vault, sealed-secrets, ...) — your
Secret should provide whichever of the keys below your setup needs
(`COMPARIA_DB_URI`, `COMPARIA_REDIS_HOST`, `ALTCHA_HMAC_KEY`,
`OPENROUTER_API_KEY`, `ALBERT_KEY`, `HF_INFERENCE_KEY`, `ORDBOGEN_API_KEY`,
`LINKUP_API_KEY`, `MISTRAL_API_KEY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and
`HF_PUSH_DATASET_PATH`/`HF_PUSH_DATASET_KEY` if you use dataset export). In
this mode the chart cannot validate that a required key is present — that is
your Secret's responsibility.

Otherwise, the chart renders a `Secret` from these values:

| Value                       | Required | Description                              |
| ----------------------------- | -------- | ----------------------------------------- |
| `secrets.dbUri`                | yes      | `COMPARIA_DB_URI`, e.g. `postgresql://user:pass@host:5432/db` |
| `secrets.redisHost`            | yes      | `COMPARIA_REDIS_HOST`                     |
| `secrets.altchaHmacKey`        | yes      | `ALTCHA_HMAC_KEY`, e.g. `openssl rand -hex 32` |
| `secrets.openrouterApiKey`     | at least one of these four | `OPENROUTER_API_KEY` |
| `secrets.albertKey`            | at least one of these four | `ALBERT_KEY` |
| `secrets.hfInferenceKey`       | at least one of these four | `HF_INFERENCE_KEY` |
| `secrets.ordbogenApiKey`       | at least one of these four | `ORDBOGEN_API_KEY` |
| `secrets.linkupApiKey`         | no       | `LINKUP_API_KEY`, enables web search      |
| `secrets.mistralApiKey`        | no       | `MISTRAL_API_KEY`, Mistral moderation API. Left empty, prompt checks (content safety, personal data) no-op |
| `secrets.smtpUsername`         | no       | `SMTP_USERNAME`. Only relevant when `config.smtp.host` is set |
| `secrets.smtpPassword`         | no       | `SMTP_PASSWORD`. Only relevant when `config.smtp.host` is set |

### Automatic database migrations

A Job runs `alembic upgrade head` against the backend image, wired to the
same Secret as the rest of the release. It is annotated
`helm.sh/hook: pre-install,pre-upgrade` with
`helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded`, so it runs
and is replaced automatically on every install and upgrade. It is not
toggleable.

### Maintenance cronjobs (`cronjobs.*`)

Each of the three is independently toggleable — there is no combined switch.

| Value                              | Default | Description |
| ------------------------------------ | ------- | ------------ |
| `cronjobs.ranking.enabled`           | `true`  | Recomputes the leaderboard. No external side effects. |
| `cronjobs.ranking.schedule`          | `"17 * * * *"` | |
| `cronjobs.exportDataset.enabled`     | `false` | Exports datasets to HuggingFace. Off by default so no instance pushes data anywhere until deliberately configured. |
| `cronjobs.exportDataset.schedule`    | `"15 4 * * *"` | |
| `cronjobs.exportDataset.hfRepo`      | `""`    | `{organisation}/{repo_prefix}` on HuggingFace. Required when enabled. |
| `cronjobs.exportDataset.hfToken`     | `""`    | HuggingFace token with write access to `hfRepo`. Required when enabled. |
| `cronjobs.analyze.enabled`           | `false` | LLM-based moderation/data-quality pass, consumes `OPENROUTER_API_KEY`. Off by default so enabling it — and paying for the LLM calls — is deliberate. |
| `cronjobs.analyze.schedule`          | `"35 3 * * *"` | |

#### Dataset export

The export destination (HuggingFace repo path + token) is stored in the
database and configured through the admin panel, not read by the export
CronJob itself. `cronjobs.exportDataset.hfRepo`/`hfToken` are only consumed
once: the pre-install/pre-upgrade migration hook seeds an initial destination
row from them the first time it runs against a fresh database. After that,
manage the destination from the admin panel; changing `hfRepo`/`hfToken` in
values has no further effect.

### Ingress (`ingress.*`)

Off by default — a working Ingress controller/TLS setup cannot be safely
assumed.

| Value                | Default | Description |
| ---------------------- | ------- | ------------ |
| `ingress.enabled`      | `false` | |
| `ingress.host`         | `""`    | Required when enabled |
| `ingress.path`         | `/`     | Path prefix for this release's own routes. See [Shared-domain topology](#shared-domain-topology-beta-gouv-specific) below |
| `ingress.className`    | `""`    | |
| `ingress.annotations`  | `{}`    | Passed through as-is, e.g. for cert-manager |
| `ingress.tls`          | `[]`    | Passed through as-is |

Routes `/counter`, `/models/`, and `/arena/` to the backend Service and
everything else to the frontend Service, mirroring
[`devops/standalone_docker_install/Caddyfile`](../standalone_docker_install/Caddyfile).
Other backend endpoints (auth, admin, ...) are called server-side by the
frontend over the cluster-internal `PUBLIC_API_LOCAL_URL`, not through this
Ingress.

#### Shared-domain topology (beta.gouv-specific)

This section describes how beta.gouv runs `comparia.beta.gouv.fr`, not the
generic self-hosting case above — skip it unless you're deliberately
reproducing that topology. It does not change any default in this chart:
`ingress.path` defaults to `/`, so a plain install is unaffected.

beta.gouv splits the landing pages (home, news, product, ...) into a
separate app and chart,
[`comparia-landing`](https://github.com/betagouv/ComparIA-landing/tree/main/devops/helm/comparia-landing),
installed as its own release at the domain root. This chart's release then
owns only the arena app, mounted at a subpath (`/arena` by default, matching
`comparia-landing`'s `PUBLIC_ARENA_URL`). Two things have to agree for that
to work:

1. `ingress.path` on this chart, set to the subpath (e.g. `/arena`) — this
   shifts the frontend catch-all and the three backend routes above under
   that prefix, so this chart's own Ingress no longer claims `/`.
2. The frontend image (`image.frontend.tag`) built with `PUBLIC_BASE_PATH`
   set to the same value (see `frontend/svelte.config.js` /
   `frontend/.env.example` in this repo) — that's a build-time setting, so
   this requires a dedicated image build, distinct from the root-mounted one
   used by the generic self-hosting case.

This chart's Ingress still only routes its own paths; it does not know
about `comparia-landing`'s Service. Routing `/` to `comparia-landing` is a
separate Ingress resource (or a separate rule set, depending on your
ingress controller), created by whatever composes the two releases —
mirroring how `languia-infra/kustomize/overlays/*/prd/ingress.yaml` already
routes this domain today, just without the landing split yet. This chart
deliberately does not template that second Ingress: doing so would require
it to know the other chart's release name and Service naming convention,
coupling two otherwise-independent, self-contained charts.

## Upgrading

Two upgrade shapes, do not mix them:

**Image-only upgrade** — bumps the app version without touching anything
else you've set (cron job toggles, Ingress, ...):

```bash
helm upgrade comparia devops/helm/comparia \
  --reuse-values \
  --set image.backend.tag=1.4.0 \
  --set image.frontend.tag=1.4.0
```

**Full-state upgrade** — explicit, complete desired state, for scripted
deploys against a values file:

```bash
helm upgrade comparia devops/helm/comparia -f values-prod.yaml
```

`--reuse-values` and `-f` do not combine reliably across Helm versions.
Mixing them on the same command can silently drop or resurrect toggles you
did not intend to change — pick one shape per pipeline.

## Development

```bash
make helm-lint   # helm lint, against devops/helm/comparia/ci/values-lint.yaml
make helm-test   # helm-unittest, see devops/helm/comparia/tests/
```

Requires the [helm-unittest](https://github.com/helm-unittest/helm-unittest)
plugin: `helm plugin install https://github.com/helm-unittest/helm-unittest`.
