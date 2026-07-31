<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Alert, Badge, Button, Input, Select } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import type { PromptCheckPatch, PromptCheckStatus } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { PageProps } from './$types'
  import type { PromptCheckDecision, PromptCheckTry } from './types'

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

  const decisionLabels: Record<PromptCheckDecision, string> = {
    pass: m['admin.promptChecks.bench.decision.pass'](),
    logged: m['admin.promptChecks.bench.decision.logged'](),
    warned: m['admin.promptChecks.bench.decision.warned'](),
    blocked: m['admin.promptChecks.bench.decision.blocked'](),
    error: m['admin.promptChecks.bench.decision.error']()
  }
  const decisionVariants = {
    pass: 'green',
    logged: 'light-info',
    warned: 'orange',
    blocked: 'red',
    error: 'purple'
  } as const
  const actionLabels: Record<Action, string> = {
    off: m['admin.promptChecks.actions.off'](),
    log: m['admin.promptChecks.actions.log'](),
    warn: m['admin.promptChecks.actions.warn'](),
    block: m['admin.promptChecks.actions.block']()
  }

  // svelte-ignore state_referenced_locally
  let draft = $state<Draft>(toDraft(data.check))
  let saving = $state(false)
  let errors = $state<Record<string, string>>({})

  let benchText = $state('')
  let benchRunning = $state(false)
  let benchError = $state('')
  let benchResult = $state<PromptCheckTry | null>(null)
  // Figé au moment de l'essai : la personne peut modifier le tableau ensuite,
  // le panneau doit rester le compte rendu de ce qui a réellement été essayé.
  let benchUsed = $state<Record<string, CategoryConfig>>({})

  // Resynchronisé chaque fois que SvelteKit recharge les données après un enregistrement.
  $effect(() => {
    draft = toDraft(data.check)
    errors = {}
  })

  const failures = $derived(data.check.consecutive_failures ?? 0)
  const categories = $derived(categoryOrder.filter((category) => category in data.check.categories))

  const decisionOrder: PromptCheckDecision[] = ['pass', 'logged', 'warned', 'blocked', 'error']
  const stats = $derived(data.stats ?? null)
  const statsDays = $derived(data.statsDays ?? stats?.days ?? 30)
  const statsCategories = $derived(
    Object.entries(stats?.by_category ?? {}).sort((a, b) => b[1] - a[1])
  )

  const benchRows = $derived.by(() => {
    const result = benchResult
    if (!result) return []
    const known = new Set([...Object.keys(benchUsed), ...Object.keys(result.scores)])
    const ordered = [
      ...categoryOrder.filter((category) => known.has(category)),
      ...[...known].filter((category) => !categoryOrder.includes(category))
    ]
    return ordered.map((category) => ({
      category,
      score: result.scores[category] ?? 0,
      threshold: benchUsed[category]?.threshold ?? 0,
      action: benchUsed[category]?.action ?? ('off' as Action),
      triggered: category in result.triggered
    }))
  })

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

  function formatScore(value: number) {
    // Trois décimales, jamais arrondi à la première : 0,410 contre un seuil de
    // 0,500 est justement ce qu'un administrateur vient regarder ici.
    return value.toFixed(3).replace('.', ',')
  }

  /** Le tableau tel qu'il est à l'écran, modifications non enregistrées comprises. */
  function readDraft() {
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
    return { categories, fieldErrors }
  }

  async function runBench() {
    const { categories, fieldErrors } = readDraft()
    errors = fieldErrors
    if (Object.keys(fieldErrors).length > 0) return

    const text = benchText.trim()
    if (text === '') {
      benchResult = null
      benchError = m['admin.promptChecks.bench.empty']()
      return
    }

    benchRunning = true
    benchError = ''
    try {
      const result = await api.request<PromptCheckTry>('/admin/prompt-check/try', {
        method: 'POST',
        body: JSON.stringify({ text, categories, model: draft.model })
      })
      benchUsed = categories
      benchResult = result
    } catch (error) {
      benchResult = null
      benchError = (error as Error).message
    } finally {
      benchRunning = false
    }
  }

  async function save(event: SubmitEvent) {
    event.preventDefault()

    const { categories, fieldErrors } = readDraft()
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

    <section id="prompt-check-bench" class="mt-10">
      <h2 class="fr-h5 mb-1!">{m['admin.promptChecks.bench.title']()}</h2>
      <p class="fr-hint-text mt-0!">{m['admin.promptChecks.bench.hint']()}</p>

      <div class={['fr-input-group', { 'fr-input-group--error': !!benchError }]}>
        <label class="fr-label" for="prompt-check-bench-text">
          {m['admin.promptChecks.bench.label']()}
          <span class="fr-hint-text">{m['admin.promptChecks.bench.labelHint']()}</span>
        </label>
        <textarea
          id="prompt-check-bench-text"
          class="fr-input"
          rows="4"
          bind:value={benchText}
          disabled={benchRunning}
          aria-describedby="prompt-check-bench-messages"
        ></textarea>
        {#if benchError}
          <div class="fr-messages-group" id="prompt-check-bench-messages" aria-live="polite">
            <p class="fr-message fr-message--error">{benchError}</p>
          </div>
        {/if}
      </div>

      <Button
        id="prompt-check-bench-run"
        variant="secondary"
        onclick={runBench}
        text={benchRunning
          ? m['admin.promptChecks.bench.running']()
          : m['admin.promptChecks.bench.run']()}
        disabled={benchRunning}
      />

      {#if benchResult}
        <div
          id="prompt-check-bench-result"
          class="mt-6 p-4 border border-[--border-default-grey]"
          aria-live="polite"
        >
          <h3 class="fr-h6 mb-2!">{m['admin.promptChecks.bench.resultTitle']()}</h3>

          <p class="gap-2 mb-4 flex flex-wrap items-center">
            <span class="fr-text--sm">{m['admin.promptChecks.bench.decisionLegend']()}</span>
            <Badge
              id="prompt-check-bench-decision"
              size="sm"
              variant={decisionVariants[benchResult.decision]}
              text={decisionLabels[benchResult.decision]}
            />
            <span class="fr-text--sm text-[--text-mention-grey]">
              {m['admin.promptChecks.bench.latency']({ count: benchResult.latency_ms })}
            </span>
          </p>

          <h4 class="fr-text--sm mb-1! font-bold">
            {m['admin.promptChecks.bench.messageTitle']()}
          </h4>
          <p class="fr-text--sm" id="prompt-check-bench-message">
            {benchResult.message ?? m['admin.promptChecks.bench.messageNone']()}
          </p>

          <h4 class="fr-text--sm mb-1! font-bold">{m['admin.promptChecks.bench.scoresTitle']()}</h4>
          <p class="fr-hint-text mt-0!">{m['admin.promptChecks.bench.scoresHint']()}</p>

          <div class="fr-table fr-table--bordered mb-0!">
            <div class="fr-table__wrapper">
              <div class="fr-table__container">
                <div class="fr-table__content">
                  <table id="prompt-check-bench-scores">
                    <caption class="fr-sr-only">{m['admin.promptChecks.bench.caption']()}</caption>
                    <thead>
                      <tr>
                        <th scope="col">{m['admin.promptChecks.columns.category']()}</th>
                        <th scope="col">{m['admin.promptChecks.bench.columns.score']()}</th>
                        <th scope="col">{m['admin.promptChecks.columns.threshold']()}</th>
                        <th scope="col">{m['admin.promptChecks.columns.action']()}</th>
                        <th scope="col">{m['admin.promptChecks.bench.columns.verdict']()}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {#each benchRows as row (row.category)}
                        <tr id={`prompt-check-bench-row-${row.category}`}>
                          <th scope="row" class="font-normal">{categoryLabel(row.category)}</th>
                          <td class="tabular-nums">{formatScore(row.score)}</td>
                          <td class="tabular-nums">{formatScore(row.threshold)}</td>
                          <td>{actionLabels[row.action]}</td>
                          <td>
                            {#if row.triggered}
                              <Badge
                                size="sm"
                                variant="orange"
                                text={m['admin.promptChecks.bench.triggered']()}
                              />
                            {:else if row.action === 'off'}
                              <span class="fr-text--sm text-[--text-mention-grey]">
                                {m['admin.promptChecks.bench.ignored']()}
                              </span>
                            {:else}
                              <span class="fr-text--sm text-[--text-mention-grey]">
                                {m['admin.promptChecks.bench.notTriggered']()}
                              </span>
                            {/if}
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      {/if}
    </section>

    <section id="prompt-check-stats" class="mt-10">
      <h2 class="fr-h5 mb-1!">{m['admin.promptChecks.stats.title']()}</h2>
      {#if !stats}
        <p class="fr-text--sm text-[--text-mention-grey]">
          {m['admin.promptChecks.stats.unavailable']()}
        </p>
      {:else}
        <p class="fr-hint-text mt-0!">
          {m['admin.promptChecks.stats.window']({ days: statsDays })}
        </p>
        <p class="fr-text--lead mb-4!" id="prompt-check-stats-total">
          {m['admin.promptChecks.stats.total']({ count: stats.total })}
        </p>

        <h3 class="fr-h6 mb-1!">{m['admin.promptChecks.stats.byDecisionTitle']()}</h3>
        <ul class="fr-text--sm mb-4 ps-4">
          {#each decisionOrder as decision (decision)}
            <li id={`prompt-check-stats-decision-${decision}`}>
              {decisionLabels[decision]} : {stats.by_decision[decision] ?? 0}
            </li>
          {/each}
        </ul>

        <h3 class="fr-h6 mb-1!">{m['admin.promptChecks.stats.byCategoryTitle']()}</h3>
        {#if statsCategories.length === 0}
          <p class="fr-text--sm text-[--text-mention-grey]">
            {m['admin.promptChecks.stats.byCategoryNone']()}
          </p>
        {:else}
          <ul class="fr-text--sm mb-4 ps-4">
            {#each statsCategories as [category, count] (category)}
              <li id={`prompt-check-stats-category-${category}`}>
                {categoryLabel(category)} : {count}
              </li>
            {/each}
          </ul>
        {/if}

        <h3 class="fr-h6 mb-1!">{m['admin.promptChecks.stats.warningsTitle']()}</h3>
        <p class="fr-text--sm" id="prompt-check-stats-warnings">
          {m['admin.promptChecks.stats.warningsShown']({ count: stats.warnings_shown })}, {m[
            'admin.promptChecks.stats.proceeded'
          ]({ count: stats.proceeded })}
        </p>
        <p class="fr-hint-text mt-0!">{m['admin.promptChecks.stats.warningsHint']()}</p>
      {/if}
    </section>
  </div>
</PageLayout>
