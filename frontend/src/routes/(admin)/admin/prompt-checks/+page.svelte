<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Alert, Badge, Button, Input, Segmented } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import type { PromptCheckPatch, PromptCheckStatus } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { PageProps } from './$types'

  type Kind = PromptCheckStatus['kind']
  type Mode = PromptCheckStatus['mode']
  type Draft = { mode: Mode; model: string; thresholds: Record<string, string | number> }

  let { data }: PageProps = $props()

  // Rejected by the API rather than ignored, so an admin cannot believe a
  // threshold has been set on them.
  const neverBlocking = ['health', 'law', 'financial']

  const modeOptions: { value: Mode; label: string }[] = [
    { value: 'off', label: m['admin.promptChecks.mode.off']() },
    { value: 'log', label: m['admin.promptChecks.mode.log']() },
    { value: 'warn', label: m['admin.promptChecks.mode.warn']() },
    { value: 'block', label: m['admin.promptChecks.mode.block']() }
  ]
  const kindLabels: Record<Kind, string> = {
    content_safety: m['admin.promptChecks.kind.contentSafety'](),
    pii: m['admin.promptChecks.kind.pii']()
  }
  const kindHints: Record<Kind, string> = {
    content_safety: m['admin.promptChecks.kindHint.contentSafety'](),
    pii: m['admin.promptChecks.kindHint.pii']()
  }
  const categoryLabels: Record<string, string> = {
    sexual: m['admin.promptChecks.categories.sexual'](),
    hate_and_discrimination: m['admin.promptChecks.categories.hateAndDiscrimination'](),
    violence_and_threats: m['admin.promptChecks.categories.violenceAndThreats'](),
    dangerous: m['admin.promptChecks.categories.dangerous'](),
    criminal: m['admin.promptChecks.categories.criminal'](),
    selfharm: m['admin.promptChecks.categories.selfharm'](),
    health: m['admin.promptChecks.categories.health'](),
    financial: m['admin.promptChecks.categories.financial'](),
    law: m['admin.promptChecks.categories.law'](),
    pii: m['admin.promptChecks.categories.pii'](),
    jailbreaking: m['admin.promptChecks.categories.jailbreaking']()
  }

  // svelte-ignore state_referenced_locally
  let drafts = $state<Record<string, Draft>>(toDrafts(data.checks))
  let saving = $state<Kind | null>(null)
  let errors = $state<Record<string, Record<string, string>>>({})

  // Resynchronized whenever SvelteKit refreshes the page data after a save.
  $effect(() => {
    drafts = toDrafts(data.checks)
    errors = {}
  })

  function toDrafts(checks: PromptCheckStatus[]): Record<string, Draft> {
    return Object.fromEntries(
      checks.map((check) => [
        check.kind,
        {
          mode: check.mode,
          model: check.model,
          thresholds: Object.fromEntries(
            Object.entries(check.thresholds).map(([category, value]) => [category, String(value)])
          )
        }
      ])
    )
  }

  function categoryLabel(category: string) {
    return categoryLabels[category] ?? category
  }

  async function save(event: SubmitEvent, kind: Kind) {
    event.preventDefault()
    const draft = drafts[kind]
    if (!draft) return

    const thresholds: Record<string, number> = {}
    const fieldErrors: Record<string, string> = {}
    for (const [category, value] of Object.entries(draft.thresholds)) {
      // A number input binds back a number, not the string toDrafts put there.
      const raw = String(value).trim()
      const parsed = Number(raw)
      if (raw === '' || Number.isNaN(parsed) || parsed < 0 || parsed > 1) {
        fieldErrors[category] = m['admin.promptChecks.thresholds.invalid']()
      } else {
        thresholds[category] = parsed
      }
    }
    errors = { ...errors, [kind]: fieldErrors }
    if (Object.keys(fieldErrors).length > 0) return

    saving = kind
    try {
      const patch: PromptCheckPatch = { mode: draft.mode, model: draft.model, thresholds }
      await api.request<PromptCheckStatus>(`/admin/prompt-checks/${kind}`, {
        method: 'PATCH',
        body: JSON.stringify(patch)
      })
      useToast(m['admin.promptChecks.saved'](), 4000)
      await invalidate('admin:prompt-checks')
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      saving = null
    }
  }
</script>

<PageLayout
  seoTitle={m['admin.promptChecks.title']()}
  title={m['admin.promptChecks.title']()}
  subtitle={m['admin.promptChecks.subtitle']()}
>
  <p class="fr-text--sm max-w-[720px] text-[--text-mention-grey]">
    {m['admin.promptChecks.intro']()}
  </p>

  {#each data.checks as check (check.kind)}
    {@const draft = drafts[check.kind]}
    {@const failures = check.consecutive_failures ?? 0}
    <section class="mt-8 max-w-[720px]">
      <h2 class="fr-h4 mb-1!">{kindLabels[check.kind]}</h2>
      <p class="fr-text--sm text-[--text-mention-grey]">{kindHints[check.kind]}</p>

      {#if check.healthy === false}
        <Alert variant="error" title={m['admin.promptChecks.health.unhealthy']()} class="mb-4">
          <p>{m['admin.promptChecks.health.unhealthyHint']()}</p>
          <p>{m['admin.promptChecks.health.failures']({ count: failures })}</p>
        </Alert>
      {:else}
        <p class="gap-2 mb-4 flex flex-wrap items-center">
          <Badge size="sm" variant="green" text={m['admin.promptChecks.health.healthy']()} />
          <span class="fr-text--sm text-[--text-mention-grey]">
            {failures > 0
              ? m['admin.promptChecks.health.failures']({ count: failures })
              : m['admin.promptChecks.health.noFailure']()}
          </span>
        </p>
      {/if}

      {#if (check.warnings_shown ?? 0) > 0}
        <p class="fr-text--sm mb-4 text-[--text-mention-grey]">
          {check.warnings_shown === 1
            ? m['admin.promptChecks.warningsShown.countOne']()
            : m['admin.promptChecks.warningsShown.count']({ count: check.warnings_shown ?? 0 })}
          <br />
          {m['admin.promptChecks.warningsShown.hint']()}
        </p>
      {/if}

      {#if draft}
        <form onsubmit={(event) => save(event, check.kind)}>
          <Segmented
            id={`prompt-check-${check.kind}-mode`}
            legend={m['admin.promptChecks.mode.legend']()}
            options={modeOptions}
            bind:value={draft.mode}
          />
          <p class="fr-hint-text mt-2!">{m['admin.promptChecks.mode.help']()}</p>

          <fieldset class="mt-6! p-0 border-0">
            <legend class="fr-h6 mb-1!">{m['admin.promptChecks.thresholds.title']()}</legend>
            <p class="fr-hint-text mt-0!">{m['admin.promptChecks.thresholds.hint']()}</p>
            <div class="gap-x-6 md:grid-cols-2 grid">
              {#each Object.keys(draft.thresholds) as category (category)}
                <Input
                  id={`prompt-check-${check.kind}-threshold-${category}`}
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  label={categoryLabel(category)}
                  bind:value={draft.thresholds[category]}
                  error={errors[check.kind]?.[category]}
                  disabled={saving === check.kind}
                />
              {/each}
            </div>
          </fieldset>

          <div class="mt-6">
            <h3 class="fr-h6 mb-1!">{m['admin.promptChecks.neverBlock.title']()}</h3>
            <p class="fr-hint-text mt-0!">{m['admin.promptChecks.neverBlock.hint']()}</p>
            <ul class="gap-2 p-0 flex list-none flex-wrap">
              {#each neverBlocking as category (category)}
                <li>
                  <Badge
                    size="sm"
                    variant="orange"
                    text={`${categoryLabel(category)} : ${m['admin.promptChecks.neverBlock.badge']()}`}
                  />
                </li>
              {/each}
            </ul>
          </div>

          <Input
            id={`prompt-check-${check.kind}-model`}
            label={m['admin.promptChecks.model.label']()}
            help={m['admin.promptChecks.model.hint']()}
            bind:value={draft.model}
            disabled={saving === check.kind}
            groupClass="mt-6!"
          />

          <Button
            type="submit"
            text={saving === check.kind
              ? m['admin.promptChecks.saving']()
              : m['admin.promptChecks.save']()}
            disabled={saving === check.kind}
            class="mt-4"
          />
        </form>
      {/if}
    </section>
  {/each}
</PageLayout>
