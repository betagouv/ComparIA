# The admin panel

Almost everything that makes one instance different from another lives at `/admin`, in the database, editable while the instance runs. The `.env` file holds only what has to exist before the app starts: database, Redis, API keys, SMTP.

You need an admin account to get in. Put your email in `ADMIN_EMAILS` and restart the backend; the account is created if it does not exist and promoted if it does.

```
ADMIN_EMAILS='["you@example.com"]'
```

On an instance that is already running, `./comparia-cli db seed-admins` does the same thing without a restart.

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

`/admin/utilisateurs` is where you search accounts, change roles, invite people by email and delete an account. Anyone in `ADMIN_EMAILS` gets admin again on every restart, so remove them from the env before demoting them here.

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
