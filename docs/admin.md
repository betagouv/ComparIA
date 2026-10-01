# The admin panel

Almost everything that makes one instance different from another lives at `/admin`, in the database, editable while the instance runs. The `.env` file holds only what has to exist before the app starts: database, Redis, API keys, SMTP.

You need an admin account to get in. Put your email in `ADMIN_EMAILS` and restart the backend; the account is created if it does not exist and promoted if it does.

```
ADMIN_EMAILS='["you@example.com"]'
```

On an instance that is already running, `./comparia-cli db seed-admins` does the same thing without a restart.

## Two-factor authentication

Every admin has to pair an authenticator app (Google Authenticator, Aegis, FreeOTP, or any app that reads a QR code and shows six digits). The first time an admin opens `/admin` without one, they land on `/settings` and are asked to set it up; after that, signing in asks for the email code and then the six digits. An admin who has just been invited or promoted should pair their app straight away: until they do, anyone holding their session can pair a device in their name.

The app's secrets are encrypted in the database with `COMPARIA_ENCRYPTION_KEY`. The backend refuses to start without one outside debug mode, and refuses to start anywhere with one that is not a Fernet key (a hex string from `openssl rand -hex 32` is not). The migration job needs the same variable, since `backend.config` checks it at import before Alembic runs. Generate one with:

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

To rotate it, put the new key first and keep the old one after a comma: `COMPARIA_ENCRYPTION_KEY=new,old`. Each admin's secret is re-encrypted with the new key the next time they sign in, so the old key can go once everyone has.

An admin changes device from `/settings`: a code from the current app, then the new QR code. Their other sessions are signed out when the new app is confirmed.

An admin who lost their phone asks another admin, who opens `/admin/utilisateurs` and uses the reset action on their row. That signs them out everywhere and sends them back to the setup screen at their next visit. Do this over a channel you trust, since the email code alone then opens the admin area again. Nobody can reset their own row.

If the only admin is locked out, there is no button left. Run the same reset from the machine that has the database:

```bash
./comparia-cli db reset-totp admin@example.org
# or: make db-reset-totp EMAIL=admin@example.org
```

Then sign in with an email code and set the app up again from `/settings`.

## LLMs

`/admin/llms` has four tabs, and the order matters, because a model points at the other three.

**Labs** are who made the model: name, country of origin, logo. **Licences** carry the name, the kind, and whether reuse and commercial use are allowed. **Endpoints** are where requests go: `api_type` (the LiteLLM provider), `api_base`, and the API key. Several models normally share one endpoint.

**LLMs** are the models themselves. Each one names a lab, a licence and an endpoint, plus the `api_model_id` the provider expects, prices per token, parameter count, context window, and the openness flags the model catalogue displays: public weights, public training data, public training code, EU-hostable.

Status decides what the arena does with a model:

| Status | Meaning |
| --- | --- |
| `enabled` | drawn in matches |
| `disabled` | not drawn, still shown in past conversations |
| `archived` | retired, kept for the record and the leaderboard |

Adding models one by one through the panel is fine for a handful. For more, write them to JSON and import:

```bash
./comparia-cli llms import path/to/llms-data.json
```

`./comparia-cli llms export` writes the current catalogue to `data/llms-data.json`, which is the easiest way to see what the format looks like.

## Customization

`/admin/customization` controls the platform name, logo, the four brand colours (primary and secondary, each in a light and a dark variant), the homepage link, and the vote target the public counter counts towards.

## Languages

`/admin/locales` sets which languages the instance offers and which one it defaults to. The default has to be one of the enabled ones.

Five locales are wired up: `fr`, `da`, `en`, `lt`, `sv`. There are more translation files in `frontend/locales/messages/`, but a locale is only selectable once it is added to `SUPPORTED_LOCALES` in `utils/database/models/app_settings.py`.

## Authentication

`/admin/authentification` decides whether people can use the arena without an account.

- `anonymous_first`: anyone can vote, signing in is optional. The default.
- `sign_in_required`: no arena without a session.

An optional domain allowlist restricts who can ask for a login code, which is how you keep an instance to one organisation.

## Legal pages

`/admin/legal` holds the terms, privacy policy, the participation conditions, and any extra informational pages. Terms and the privacy policy are versioned: you edit a draft and publish it, and the published version is what visitors see.

## Users

`/admin/utilisateurs` is where you search accounts, change roles, invite people by email, reset someone's two-factor authentication and delete an account. Anyone in `ADMIN_EMAILS` gets admin again on every restart, so remove them from the env before demoting them here.

## Audience measurement

Matomo only stays exempt from consent while its data is kept apart from the arena's. Comparisons no longer keep the Matomo visitor id, but older rows may still hold one. Count them, then clear them:

```bash
make db-clear-visitor-ids            # counts, changes nothing
make db-clear-visitor-ids COMMIT=1   # clears them
```

### Inactive accounts

`comparia-cli db purge-inactive --months N` (or `make db-purge-inactive MONTHS=N`) removes accounts nobody has signed into for N months. The default is 12. It is a dry run until you pass `--apply` (`APPLY=1` with make): it lists who would get the warning, who would be erased, which rows asked for a login code but never signed in, and which admins would have matched. Run it that way from the CLI first to preview what the CronJob below will do.

An account is first warned by email, once, 30 days before the deadline or as soon as it is found past it, in the language the person accepted the terms in. It is erased at the later of the deadline and 30 days after the warning, unless the person signs in again meanwhile, which resets the clock. Erasure is what the person gets when they delete their own account from the settings page, which goes further than a deletion from the admin panel: sessions are revoked, login codes and invite links go, the email address is replaced by a placeholder, the consent proof is kept without its address, and the conversations stay in the research datasets with no link back to the person. Rows that asked for a login code but never signed in are erased without a warning once past the deadline, as there was never an account to keep. Accounts holding an invite that can still be accepted are left alone. Admins are never erased, only listed. "Signed in" is what counts, not visits: a session lasts `AUTH_SESSION_LENGTH_DAYS` (30 by default), so the command refuses a number of months whose window, 30 days of notice included, would reach an account still on a live session.

The Helm chart carries a weekly CronJob for it, `cronjobs.purgeInactive`, off by default. Before you turn it on, publish a privacy policy that states the retention period you chose, and check SMTP is set up: the CronJob reads the same `config.smtp.*` and `config.appUrl` values as the backend, and without them no warning goes out and nothing is erased.

### Retention

`comparia-cli db purge-retention` (or `make db-purge-retention`) applies the other retention periods of the privacy policy. Each rule runs on its own, in batches of 5,000 rows, so a run that stops halfway is picked up by the next one. Defaults, all overridable on the command line:

- comparison IP addresses are replaced by `erased` after 3 months (`--ip-months`). Nothing in the app reads them back.
- comparisons lose their account, Matomo visitor id and anonymous session hash after 24 months (`--comparison-months`). The conversation text and votes stay, which is what the datasets are built from.
- session rows, login codes and 2FA challenges are deleted 12 months after they expired or were revoked (`--session-months`). An account that still exists keeps its latest session row, with the IP and browser blanked: `purge-inactive` reads it to tell a dormant account, which gets a warning, from a login code nobody used, which does not. A consent proof that names a deleted session keeps everything but that link.
- moderation results are deleted after 12 months (`--prompt-check-months`).
- consent proofs are deleted 5 years after the account was deleted, or after the anonymous session ended for a visitor who never signed in (`--consent-years`).

Accounts themselves are left to `purge-inactive`. Like it, the command is a dry run until you pass `--apply`, and only counts the rows each rule would change. The dry run counts each rule against today's data, so the anonymous consents freed by deleting an account's proof in the same run only show up once applied.

The Helm chart runs it daily with `cronjobs.purgeRetention`, off by default. Change the periods there and in the published privacy policy together: the policy is what people were told.

## Publishing

`/admin/publication` sets where the open datasets go, and how often.

A run produces two datasets: `normal`, the open one, and `raw`, which still holds flagged comparisons. Each destination picks which of the two it receives, so an instance can publish the open dataset publicly and keep the raw one somewhere private.

Two kinds of destination:

- **Hugging Face**: a token and a repository path like `org/name`. The raw dataset goes to `org/name-raw`.
- **S3**: endpoint, bucket, optional region and key prefix. One bucket can hold several instances.

Frequency is per destination: off, daily, weekly or monthly. You choose the frequency, not the hour.

To check a run before trusting it with credentials:

```bash
make dataset-export-dry-run   # builds the datasets, sends them nowhere
```

## Prompt checks

`/admin/prompt-checks` runs two checks on what people type: content safety and personal data, both against the Mistral moderation API.

For each category you choose one of four actions: off, log, warn, or block. The page has a try box for testing a prompt against the current settings, and stats on what has fired.

The API key comes from the panel if you set it there, and from `MISTRAL_API_KEY` otherwise. With neither, the checks pass everything through whatever their configured action says.

## Vote tags

`/admin/vote-tags` lists the reasons offered to someone who has just voted. Each tag has an emoji, a sign saying whether it is praise or criticism, a label per language, and a display order. They are per instance, so a sector-specific arena can ask about what matters to it.

Tags are archived rather than deleted, so old votes keep meaning something.

## Suggestions

`/admin/suggestions` holds the starter prompts on an empty arena page, grouped into categories. Both categories and prompts are per language, so each locale gets its own.
