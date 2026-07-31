<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Alert, Badge, Button, Input, Select } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import type { PromptCheckPatch, PromptCheckStatus } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { PageProps } from './$types'

  type Action = 'off' | 'log' | 'warn' | 'block'
  type CategoryConfig = { threshold: number; action: Action }
  type DraftRow = { threshold: string | number; action: Action }
  type Draft = { model: string; categories: Record<string, DraftRow> }

  let { data }: PageProps = $props()

  // Réglées sur « désactivée » au départ plutôt qu'interdites : sur une instance
  // santé ou juridique, agir sur elles reviendrait à refuser les messages qui
  // font l'objet de la plateforme.
  const offByDefault = ['health', 'law', 'financial']

  // Postgres returns jsonb keys ordered by length then bytes, which would
  // scatter the frozen rows through the table. Fixed order instead, with them
  // grouped at the end.
  const categoryOrder = [
    'sexual',
    'selfharm',
    'hate_and_discrimination',
    'violence_and_threats',
    'dangerous',
    'criminal',
    'jailbreaking',
    'pii',
    ...offByDefault
  ]

  const actionOptions: { value: Action; label: string }[] = [
    { value: 'off', label: m['admin.promptChecks.actions.off']() },
    { value: 'log', label: m['admin.promptChecks.actions.log']() },
    { value: 'warn', label: m['admin.promptChecks.actions.warn']() },
    { value: 'block', label: m['admin.promptChecks.actions.block']() }
  ]
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
  let draft = $state<Draft>(toDraft(data.check))
  let saving = $state(false)
  let errors = $state<Record<string, string>>({})

  // Resynchronisé chaque fois que SvelteKit recharge les données après un enregistrement.
  $effect(() => {
    draft = toDraft(data.check)
    errors = {}
  })

  const failures = $derived(data.check.consecutive_failures ?? 0)
  const warningsShown = $derived(data.check.warnings_shown ?? 0)
  const categories = $derived(categoryOrder.filter((category) => category in data.check.categories))

  function config(check: PromptCheckStatus, category: string): CategoryConfig {
    return check.categories[category] as unknown as CategoryConfig
  }

  function toDraft(check: PromptCheckStatus): Draft {
    return {
      model: check.model,
      categories: Object.fromEntries(
        Object.keys(check.categories).map((category) => {
          const { threshold, action } = config(check, category)
          return [category, { threshold: String(threshold), action }]
        })
      )
    }
  }

  function categoryLabel(category: string) {
    return categoryLabels[category] ?? category
  }

  async function save(event: SubmitEvent) {
    event.preventDefault()

    const categories: Record<string, CategoryConfig> = {}
    const fieldErrors: Record<string, string> = {}
    for (const [category, row] of Object.entries(draft.categories)) {
      // Un champ de type number renvoie un nombre, pas la chaîne posée par toDraft.
      const raw = String(row.threshold).trim()
      const parsed = Number(raw)
      if (raw === '' || Number.isNaN(parsed) || parsed < 0 || parsed > 1) {
        fieldErrors[category] = m['admin.promptChecks.threshold.invalid']()
      } else {
        categories[category] = { threshold: parsed, action: row.action }
      }
    }
    errors = fieldErrors
    if (Object.keys(fieldErrors).length > 0) return

    saving = true
    try {
      const patch: PromptCheckPatch = {
        model: draft.model,
        categories: categories as unknown as PromptCheckPatch['categories']
      }
      await api.request<PromptCheckStatus>('/admin/prompt-check', {
        method: 'PATCH',
        body: JSON.stringify(patch)
      })
      useToast(m['admin.promptChecks.saved'](), 4000)
      await invalidate('admin:prompt-check')
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      saving = false
    }
  }
</script>

<PageLayout
  seoTitle={m['admin.promptChecks.title']()}
  title={m['admin.promptChecks.title']()}
  subtitle={m['admin.promptChecks.subtitle']()}
>
  <div class="max-w-[820px]">
    <p class="fr-text--sm text-[--text-mention-grey]">{m['admin.promptChecks.intro']()}</p>

    {#if data.check.healthy === false}
      <Alert variant="error" title={m['admin.promptChecks.health.unhealthy']()} class="my-4">
        <p>{m['admin.promptChecks.health.unhealthyHint']()}</p>
        <p>{m['admin.promptChecks.health.failures']({ count: failures })}</p>
      </Alert>
    {:else}
      <p class="gap-2 my-4 flex flex-wrap items-center">
        <Badge size="sm" variant="green" text={m['admin.promptChecks.health.healthy']()} />
        <span class="fr-text--sm text-[--text-mention-grey]">
          {failures > 0
            ? m['admin.promptChecks.health.failures']({ count: failures })
            : m['admin.promptChecks.health.noFailure']()}
        </span>
      </p>
    {/if}

    {#if warningsShown > 0}
      <p class="fr-text--sm mb-4 text-[--text-mention-grey]">
        {warningsShown === 1
          ? m['admin.promptChecks.warningsShown.countOne']()
          : m['admin.promptChecks.warningsShown.count']({ count: warningsShown })}
        <br />
        {m['admin.promptChecks.warningsShown.hint']()}
      </p>
    {/if}

    <section class="fr-callout mb-6">
      <h2 class="fr-callout__title fr-h6">{m['admin.promptChecks.actions.help.title']()}</h2>
      <ul class="fr-text--sm mb-0 ps-4">
        <li>{m['admin.promptChecks.actions.help.off']()}</li>
        <li>{m['admin.promptChecks.actions.help.log']()}</li>
        <li>{m['admin.promptChecks.actions.help.warn']()}</li>
        <li>{m['admin.promptChecks.actions.help.block']()}</li>
      </ul>
    </section>

    <form onsubmit={save}>
      <div class="fr-table fr-table--bordered">
        <div class="fr-table__wrapper">
          <div class="fr-table__container">
            <div class="fr-table__content">
              <table id="prompt-check-categories">
                <caption class="fr-sr-only">{m['admin.promptChecks.table.caption']()}</caption>
                <thead>
                  <tr>
                    <th scope="col">{m['admin.promptChecks.columns.category']()}</th>
                    <th scope="col" class="w-[140px]"
                      >{m['admin.promptChecks.columns.threshold']()}</th
                    >
                    <th scope="col" class="w-[220px]">{m['admin.promptChecks.columns.action']()}</th
                    >
                  </tr>
                </thead>
                <tbody>
                  {#each categories as category (category)}
                    <tr id={`prompt-check-row-${category}`}>
                      <th scope="row" class="font-normal">{categoryLabel(category)}</th>
                      <td>
                        <div
                          class={[
                            'fr-input-group mb-0!',
                            { 'fr-input-group--error': !!errors[category] }
                          ]}
                        >
                          <label
                            class="fr-label fr-sr-only"
                            for={`prompt-check-threshold-${category}`}
                          >
                            {m['admin.promptChecks.threshold.legend']()} : {categoryLabel(category)}
                          </label>
                          <input
                            id={`prompt-check-threshold-${category}`}
                            class="fr-input max-w-[110px]"
                            type="number"
                            min="0"
                            max="1"
                            step="0.05"
                            bind:value={draft.categories[category].threshold}
                            disabled={saving}
                            aria-describedby={`prompt-check-threshold-${category}-messages`}
                          />
                          {#if errors[category]}
                            <div
                              class="fr-messages-group"
                              id={`prompt-check-threshold-${category}-messages`}
                              aria-live="polite"
                            >
                              <p class="fr-message fr-message--error">{errors[category]}</p>
                            </div>
                          {/if}
                        </div>
                      </td>
                      <td>
                        <Select
                          id={`prompt-check-action-${category}`}
                          label={`${m['admin.promptChecks.actions.legend']()} : ${categoryLabel(category)}`}
                          hideLabel
                          options={actionOptions}
                          bind:selected={draft.categories[category].action}
                          disabled={saving}
                          groupClass="mb-0!"
                        />
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <p class="fr-hint-text mt-2!">{m['admin.promptChecks.threshold.hint']()}</p>

      <div class="mt-6">
        <h2 class="fr-h6 mb-1!">{m['admin.promptChecks.offByDefault.title']()}</h2>
        <p class="fr-hint-text mt-0!">{m['admin.promptChecks.offByDefault.hint']()}</p>
      </div>

      <Input
        id="prompt-check-model"
        label={m['admin.promptChecks.model.label']()}
        help={m['admin.promptChecks.model.hint']()}
        bind:value={draft.model}
        disabled={saving}
        groupClass="mt-6!"
      />

      <Button
        type="submit"
        text={saving ? m['admin.promptChecks.saving']() : m['admin.promptChecks.save']()}
        disabled={saving}
        class="mt-4"
      />
    </form>
  </div>
</PageLayout>
