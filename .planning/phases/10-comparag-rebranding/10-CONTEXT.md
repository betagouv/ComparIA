# Phase 10 Context — CompaRAG Full Rebranding

## Goal

Rework all pages and copy from compar:IA (LLM comparison) to CompaRAG (MCP tool comparison). Every visible string on the deployed site must read "CompaRAG" and describe MCP tool comparison, not LLM comparison.

## Decisions

**D-01** — Primary work unit is locale JSON files under `frontend/locales/messages/`. 95% of visible copy lives there. Files in scope: `fr.json`, `en.json`, `da.json`, `sv.json`, `nb_NO.json`, `lt.json`, `et.json`, `es.json`.

**D-02** — DO NOT rename localStorage keys `comparia-cohorts` and `comparia:tos`. These are session storage keys; renaming them silently breaks existing user sessions with no upside.

**D-03** — DO NOT change external URLs (digitalpublicgoods.net, huggingface.co/comparIA, metabase). These are owned externally and cannot be repointed during this phase.

**D-04** — Skip logo SVG replacement. No new logo asset exists yet. Header logo `src="/orgs/comparia.png"` stays; only the `alt` attribute text changes.

**D-05** — Skip FAQ deep rewrite. The FAQ section may reference LLM-specific concepts; a full rewrite is deferred to a future content phase.

**D-06** — The `toolArena` i18n section is already CompaRAG-native — no changes needed there.

## Out of Scope (Deferred)

- New logo SVG asset
- FAQ deep rewrite
- Renaming localStorage keys
- Changing external URLs / huggingface links
- Backend Python / FastAPI copy (no user-visible strings there)

## Hardcoded File Inventory

7 files with hardcoded `compar:IA` / `comparia` references (confirmed by grep):

| File | Reference | Constraint |
|---|---|---|
| `src/lib/components/header/Header.svelte:78` | `src="/orgs/comparia.png"` | Keep src (no asset), update alt only |
| `src/lib/components/Newsletter.svelte:31` | `title="Infolettre compar:IA"` | Rename to "CompaRAG Newsletter" |
| `src/lib/logger.server.ts:17` | `app: 'comparia-frontend'` | Rename to `'comparag-frontend'` |
| `src/routes/(pages)/ranking/+page.svelte:75` | download filename `comparia_model-*` | Rename to `comparag_model-*` |
| `src/routes/(pages)/ranking/components/Methodology.svelte:51` | download filename `comparia_model-*` | Rename to `comparag_model-*` |
| `src/error.html:269` | `Le service compar:IA rencontre...` | Rewrite to CompaRAG |
| `src/lib/global.svelte.ts:12,56` | `comparia.beta.gouv.fr` domain references | Internal domain — update if CompaRAG deployment domain is set, else leave |

Note: `src/lib/stores/cohortStore.svelte.ts` has `COHORT_STORAGE_KEY = 'comparia-cohorts'` — DO NOT change (D-02).

## Locale File Occurrence Counts

| File | Occurrences |
|---|---|
| fr.json | 47 |
| en.json | 31 |
| sv.json | 23 |
| nb_NO.json | 16 |
| da.json | 14 |
| et.json | 7 |
| lt.json | 4 |
| es.json | 1 |

## Rebranding Rules for Locale Copy

1. `compar:IA` → `CompaRAG` (exact case, always)
2. LLM/model comparison descriptions → MCP tool comparison descriptions
   - "Compare language models" → "Compare MCP tools"
   - "AI models" → "MCP tools"
   - Hero subtitle should describe: blind comparison of MCP servers on same task
3. Navigation tab descriptions that reference LLMs → rewrite for MCP tool context
4. Product/arena page descriptions → emphasize equifinality: same task, same goal, different tools

## Deployment

- Staging: comparag-beta.vercel.app (verified by human in Task 3 checkpoint)
- Push to main branch triggers Vercel deploy
