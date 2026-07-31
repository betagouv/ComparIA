<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Alert, Button, Icon, Input } from '$components/dsfr'
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

  // Réglées sur « ignorer » au départ plutôt qu'interdites : sur une instance
  // santé ou juridique, agir sur elles reviendrait à refuser les messages qui
  // font l'objet de la plateforme.
  const offByDefault = ['health', 'law', 'financial']

  // Postgres returns jsonb keys ordered by length then bytes, which would
  // scatter the frozen rows through the list. Fixed order instead, with them
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

  // Quatre teintes séparées de bout en bout : le jaune remplace l'orange DSFR,
  // trop proche du rouge pour être distingué du refus, y compris sans daltonisme.
  // Chaque teinte porte en plus une icône et un mot, jamais la couleur seule.
  const actionTone: Record<Action, { color: string; icon: string }> = {
    off: { color: 'var(--grey-425-625)', icon: 'i-ri-eye-off-line' },
    log: { color: 'var(--info-425-625)', icon: 'i-ri-eye-line' },
    warn: { color: 'var(--yellow-tournesol-main-731)', icon: 'i-ri-alert-line' },
    block: { color: 'var(--error-425-625)', icon: 'i-ri-forbid-line' }
  }
  const decisionTone: Record<PromptCheckDecision, string> = {
    pass: 'var(--green-emeraude-main-632)',
    logged: 'var(--info-425-625)',
    warned: 'var(--yellow-tournesol-main-731)',
    blocked: 'var(--error-425-625)',
    error: 'var(--purple-glycine-main-494)'
  }

  const actionOrder: Action[] = ['off', 'log', 'warn', 'block']
  const actionLabels: Record<Action, string> = {
    off: m['admin.promptChecks.actions.off'](),
    log: m['admin.promptChecks.actions.log'](),
    warn: m['admin.promptChecks.actions.warn'](),
    block: m['admin.promptChecks.actions.block']()
  }
  const actionHelp: Record<Action, string> = {
    off: m['admin.promptChecks.actions.help.off'](),
    log: m['admin.promptChecks.actions.help.log'](),
    warn: m['admin.promptChecks.actions.help.warn'](),
    block: m['admin.promptChecks.actions.help.block']()
  }
  const summaryLabels: Record<Action, string> = {
    off: m['admin.promptChecks.summary.off'](),
    log: m['admin.promptChecks.summary.log'](),
    warn: m['admin.promptChecks.summary.warn'](),
    block: m['admin.promptChecks.summary.block']()
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

  const decisionLabels: Record<PromptCheckDecision, string> = {
    pass: m['admin.promptChecks.bench.decision.pass'](),
    logged: m['admin.promptChecks.bench.decision.logged'](),
    warned: m['admin.promptChecks.bench.decision.warned'](),
    blocked: m['admin.promptChecks.bench.decision.blocked'](),
    error: m['admin.promptChecks.bench.decision.error']()
  }
  const statsDecisionLabels: Record<PromptCheckDecision, string> = {
    pass: m['admin.promptChecks.stats.decision.pass'](),
    logged: m['admin.promptChecks.stats.decision.logged'](),
    warned: m['admin.promptChecks.stats.decision.warned'](),
    blocked: m['admin.promptChecks.stats.decision.blocked'](),
    error: m['admin.promptChecks.stats.decision.error']()
  }

  // svelte-ignore state_referenced_locally
  let draft = $state<Draft>(toDraft(data.check))
  let saving = $state(false)
  let errors = $state<Record<string, string>>({})

  let benchText = $state('')
  let benchRunning = $state(false)
  let benchError = $state('')
  let benchResult = $state<PromptCheckTry | null>(null)
  // Figé au moment du test : la personne peut modifier les réglages ensuite,
  // le panneau doit rester le compte rendu de ce qui a réellement été essayé.
  let benchUsed = $state<Record<string, CategoryConfig>>({})

  // Resynchronisé chaque fois que SvelteKit recharge les données après un enregistrement.
  $effect(() => {
    draft = toDraft(data.check)
    errors = {}
  })

  const failures = $derived(data.check.consecutive_failures ?? 0)
  const categories = $derived(categoryOrder.filter((category) => category in data.check.categories))

  const summaryTiles = $derived(
    (['block', 'warn', 'log', 'off'] as Action[]).map((action) => ({
      action,
      label: summaryLabels[action],
      color: actionTone[action].color,
      icon: actionTone[action].icon,
      count: categories.filter((category) => draft.categories[category]?.action === action).length
    }))
  )
  const activeCount = $derived(
    categories.filter((category) => draft.categories[category]?.action !== 'off').length
  )

  const decisionOrder: PromptCheckDecision[] = ['pass', 'logged', 'warned', 'blocked', 'error']
  const stats = $derived(data.stats ?? null)
  const statsDays = $derived(data.statsDays ?? stats?.days ?? 30)
  const statsCategories = $derived(
    Object.entries(stats?.by_category ?? {}).sort((a, b) => b[1] - a[1])
  )
  const statsCategoriesMax = $derived(Math.max(1, ...statsCategories.map(([, count]) => count)))

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

  function percent(value: number) {
    return Math.min(100, Math.max(0, value * 100))
  }

  /** Les réglages tels qu'ils sont à l'écran, modifications non enregistrées comprises. */
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

{#snippet statusDot(color: string)}
  <span class="h-2 w-2 shrink-0 rounded-full" style="background: {color}" aria-hidden="true"></span>
{/snippet}

<PageLayout
  seoTitle={m['admin.promptChecks.title']()}
  title={m['admin.promptChecks.title']()}
  subtitle={m['admin.promptChecks.subtitle']()}
>
  <div class="gap-10 mx-auto flex max-w-[1120px] flex-col">
    <section id="prompt-check-summary">
      {#if data.check.healthy === false}
        <Alert variant="error" title={m['admin.promptChecks.health.unhealthy']()} class="mb-6">
          <p>{m['admin.promptChecks.health.unhealthyHint']()}</p>
          <p>{m['admin.promptChecks.health.failures']({ count: failures })}</p>
        </Alert>
      {/if}

      <div class="gap-3 mb-4 flex flex-wrap items-baseline justify-between">
        <h2 class="fr-h5 mb-0!">{m['admin.promptChecks.summary.title']()}</h2>
        {#if data.check.healthy !== false}
          <p
            id="prompt-check-health"
            class="gap-2 mb-0! text-sm text-grey flex flex-wrap items-center"
          >
            <span class="gap-1.5 text-dark-grey font-bold flex items-center">
              {@render statusDot('var(--green-emeraude-main-632)')}
              {m['admin.promptChecks.health.healthy']()}
            </span>
            <span>
              {failures > 0
                ? m['admin.promptChecks.health.failures']({ count: failures })
                : m['admin.promptChecks.health.noFailure']()}
            </span>
          </p>
        {/if}
      </div>

      <div class="gap-3 sm:grid-cols-4 grid grid-cols-2">
        {#each summaryTiles as tile (tile.action)}
          <div id="prompt-check-summary-{tile.action}" class="cg-border bg-white p-3">
            <p class="gap-1.5 mb-2! text-xs text-grey flex items-center">
              <Icon icon={tile.icon} size="xs" style="color: {tile.color}" aria-hidden="true" />
              {tile.label}
            </p>
            <p class="mb-0! text-dark-grey font-bold text-[28px] leading-none">{tile.count}</p>
          </div>
        {/each}
      </div>

      {#if activeCount === 0}
        <p class="mt-3 text-sm text-grey">{m['admin.promptChecks.summary.none']()}</p>
      {/if}

      <p class="mt-4 text-sm text-grey">{m['admin.promptChecks.intro']()}</p>
    </section>

    <form onsubmit={save}>
      <h2 class="fr-h5 mb-3!">{m['admin.promptChecks.categoriesTitle']()}</h2>

      <div class="mb-5 cg-border p-3 md:p-4 bg-[--cg-very-light-grey]">
        <h3 class="text-sm mb-2! text-dark-grey font-bold">
          {m['admin.promptChecks.actions.help.title']()}
        </h3>
        <ul class="gap-x-6 gap-y-2 sm:grid-cols-2 m-0! p-0! grid list-none">
          {#each actionOrder as action (action)}
            <li class="gap-2 text-sm flex items-start">
              <Icon
                icon={actionTone[action].icon}
                size="xs"
                class="mt-0.5 shrink-0"
                style="color: {actionTone[action].color}"
                aria-hidden="true"
              />
              <span class="text-grey">
                <strong class="text-dark-grey">{actionLabels[action]}</strong>
                {actionHelp[action]}
              </span>
            </li>
          {/each}
        </ul>
      </div>

      <ul
        id="prompt-check-categories"
        class="gap-2 m-0! p-0! flex list-none flex-col"
        aria-label={m['admin.promptChecks.summary.list']()}
      >
        {#each categories as category (category)}
          {@const action = draft.categories[category].action}
          <li
            id={`prompt-check-row-${category}`}
            class={[
              'cg-border ps-4 gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center p-3 grid',
              action === 'off' ? 'bg-[--cg-very-light-grey]' : 'bg-white'
            ]}
            style="box-shadow: inset 3px 0 0 {actionTone[action].color}"
          >
            <p class="mb-0! text-dark-grey min-w-0 font-medium">{categoryLabel(category)}</p>

            <div class="gap-4 flex flex-wrap items-center">
              <fieldset class="action-pills">
                <legend class="fr-sr-only"
                  >{m['admin.promptChecks.actions.legend']()} : {categoryLabel(category)}</legend
                >
                {#each actionOrder as option (option)}
                  <input
                    id={`prompt-check-action-${category}-${option}`}
                    class="sr-only"
                    type="radio"
                    name={`prompt-check-action-${category}`}
                    value={option}
                    bind:group={draft.categories[category].action}
                    disabled={saving}
                  />
                  <label
                    for={`prompt-check-action-${category}-${option}`}
                    style="--pill-color: {actionTone[option]
                      .color}; --pill-soft: color-mix(in srgb, {actionTone[option]
                      .color} 12%, transparent)"
                  >
                    <Icon
                      icon={actionTone[option].icon}
                      size="xs"
                      class="pill-icon"
                      aria-hidden="true"
                    />
                    {actionLabels[option]}
                  </label>
                {/each}
              </fieldset>

              <div
                class={['fr-input-group mb-0!', { 'fr-input-group--error': !!errors[category] }]}
              >
                <div class="gap-2 flex items-center">
                  <label
                    class="fr-label text-xs! mt-0! text-grey"
                    for={`prompt-check-threshold-${category}`}
                  >
                    {m['admin.promptChecks.threshold.legend']()}
                    <span class="fr-sr-only">: {categoryLabel(category)}</span>
                  </label>
                  <input
                    id={`prompt-check-threshold-${category}`}
                    class="fr-input w-[86px] tabular-nums"
                    type="number"
                    min="0"
                    max="1"
                    step="0.05"
                    bind:value={draft.categories[category].threshold}
                    disabled={saving}
                    aria-describedby={`prompt-check-threshold-${category}-messages`}
                  />
                </div>
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
            </div>
          </li>
        {/each}
      </ul>

      <p class="fr-hint-text mt-3!">{m['admin.promptChecks.threshold.hint']()}</p>

      <div class="mt-6">
        <h3 class="fr-h6 mb-1!">{m['admin.promptChecks.offByDefault.title']()}</h3>
        <p class="fr-hint-text mt-0!">{m['admin.promptChecks.offByDefault.hint']()}</p>
      </div>

      <Input
        id="prompt-check-model"
        label={m['admin.promptChecks.model.label']()}
        help={m['admin.promptChecks.model.hint']()}
        bind:value={draft.model}
        disabled={saving}
        groupClass="mt-6! max-w-[420px]"
      />

      <Button
        type="submit"
        text={saving ? m['admin.promptChecks.saving']() : m['admin.promptChecks.save']()}
        disabled={saving}
        class="mt-4"
      />
    </form>

    <section id="prompt-check-bench">
      <h2 class="fr-h5 mb-1!">{m['admin.promptChecks.bench.title']()}</h2>
      <p class="fr-hint-text mt-0! mb-4!">{m['admin.promptChecks.bench.hint']()}</p>

      <div class="gap-6 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)] grid items-start">
        <div>
          <div class={['fr-input-group', { 'fr-input-group--error': !!benchError }]}>
            <label class="fr-label" for="prompt-check-bench-text">
              {m['admin.promptChecks.bench.label']()}
              <span class="fr-hint-text">{m['admin.promptChecks.bench.labelHint']()}</span>
            </label>
            <textarea
              id="prompt-check-bench-text"
              class="fr-input"
              rows="8"
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
        </div>

        {#if benchResult}
          <div id="prompt-check-bench-result" class="cg-border bg-white p-4" aria-live="polite">
            <div
              class="gap-3 mb-4 pb-4 flex flex-wrap items-center border-0 border-b border-solid border-[--border-default-grey]"
            >
              <span class="text-sm text-grey">{m['admin.promptChecks.bench.decisionLegend']()}</span
              >
              <span
                id="prompt-check-bench-decision"
                class="gap-2 px-3 py-1 text-dark-grey font-bold flex items-center rounded-full"
                style="background: color-mix(in srgb, {decisionTone[
                  benchResult.decision
                ]} 14%, transparent)"
              >
                {@render statusDot(decisionTone[benchResult.decision])}
                {decisionLabels[benchResult.decision]}
              </span>
              <span class="text-sm text-grey ms-auto">
                {m['admin.promptChecks.bench.latency']({ count: benchResult.latency_ms })}
              </span>
            </div>

            <h3 class="text-sm mb-1! text-dark-grey font-bold">
              {m['admin.promptChecks.bench.messageTitle']()}
            </h3>
            <p class="text-sm mb-5!" id="prompt-check-bench-message">
              {benchResult.message ?? m['admin.promptChecks.bench.messageNone']()}
            </p>

            <h3 class="text-sm mb-1! text-dark-grey font-bold">
              {m['admin.promptChecks.bench.scoresTitle']()}
            </h3>
            <p class="fr-hint-text mt-0! mb-3!">{m['admin.promptChecks.bench.scoresHint']()}</p>

            <ul
              id="prompt-check-bench-scores"
              class="gap-3 m-0! p-0! flex list-none flex-col"
              aria-label={m['admin.promptChecks.bench.caption']()}
            >
              {#each benchRows as row (row.category)}
                {@const tone = row.triggered ? actionTone[row.action].color : 'var(--grey-425-625)'}
                <li id={`prompt-check-bench-row-${row.category}`}>
                  <div class="gap-2 mb-1 flex flex-wrap items-baseline">
                    <span class="text-sm text-dark-grey min-w-0 font-medium flex-1"
                      >{categoryLabel(row.category)}</span
                    >
                    <span class="text-dark-grey font-bold w-[4.25rem] text-right tabular-nums">
                      {formatScore(row.score)}
                    </span>
                    <span class="text-xs text-grey w-[6.5rem] text-right">
                      {#if row.triggered}
                        <strong class="text-dark-grey">
                          {m['admin.promptChecks.bench.triggered']()}
                        </strong>
                      {:else if row.action === 'off'}
                        {m['admin.promptChecks.bench.ignored']()}
                      {:else}
                        {m['admin.promptChecks.bench.notTriggered']()}
                      {/if}
                    </span>
                  </div>

                  <div
                    class="h-2 relative rounded-full"
                    style="background: color-mix(in srgb, {tone} 18%, transparent)"
                    aria-hidden="true"
                  >
                    <div
                      class="inset-y-0 left-0 absolute rounded-full"
                      style="width: {percent(row.score)}%; background: {tone}"
                    ></div>
                    <div
                      class="-inset-y-1 absolute w-[2px] rounded-full bg-[--grey-200-850]"
                      style="left: calc({percent(row.threshold)}% - 1px)"
                    ></div>
                  </div>

                  <p class="mt-1 mb-0! text-xs text-grey tabular-nums">
                    {m['admin.promptChecks.bench.threshold']({
                      value: formatScore(row.threshold)
                    })}
                  </p>
                </li>
              {/each}
            </ul>
          </div>
        {:else}
          <p
            class="cg-border text-sm p-6 text-grey flex items-center justify-center bg-[--cg-very-light-grey]"
          >
            {m['admin.promptChecks.bench.resultWaiting']()}
          </p>
        {/if}
      </div>
    </section>

    <section id="prompt-check-stats">
      <h2 class="fr-h5 mb-3!">{m['admin.promptChecks.stats.title']({ days: statsDays })}</h2>
      {#if !stats}
        <p class="text-sm text-grey">
          {m['admin.promptChecks.stats.unavailable']()}
        </p>
      {:else}
        <div class="gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] grid items-start">
          <div>
            <p id="prompt-check-stats-total" class="mb-1! text-dark-grey text-5xl font-bold">
              {stats.total}
            </p>
            <p class="mb-4! text-sm text-grey">{m['admin.promptChecks.stats.totalLabel']()}</p>

            <h3 class="text-sm mb-2! text-dark-grey font-bold">
              {m['admin.promptChecks.stats.byDecisionTitle']()}
            </h3>
            <div class="gap-2 sm:grid-cols-3 grid grid-cols-2">
              {#each decisionOrder as decision (decision)}
                <div
                  id={`prompt-check-stats-decision-${decision}`}
                  class="cg-border bg-white p-2 px-3"
                >
                  <p class="gap-1.5 mb-1! text-xs text-grey flex items-center">
                    {@render statusDot(decisionTone[decision])}
                    {statsDecisionLabels[decision]}
                  </p>
                  <p class="mb-0! text-dark-grey text-xl font-bold leading-none">
                    {stats.by_decision[decision] ?? 0}
                  </p>
                </div>
              {/each}
            </div>
          </div>

          <div>
            <h3 class="text-sm mb-2! text-dark-grey font-bold">
              {m['admin.promptChecks.stats.byCategoryTitle']()}
            </h3>
            {#if statsCategories.length === 0}
              <p class="text-sm text-grey">
                {m['admin.promptChecks.stats.byCategoryNone']()}
              </p>
            {:else}
              <ul class="gap-2 mb-6! m-0! p-0! flex list-none flex-col">
                {#each statsCategories as [category, count] (category)}
                  <li
                    id={`prompt-check-stats-category-${category}`}
                    class="gap-3 grid grid-cols-[minmax(0,13rem)_minmax(0,1fr)_auto] items-center"
                  >
                    <span class="text-sm text-grey">{categoryLabel(category)}</span>
                    <span
                      class="rounded-sm h-3 block bg-[--brand-primary-softest]"
                      aria-hidden="true"
                    >
                      <span
                        class="rounded-r-sm block h-full bg-[--brand-primary]"
                        style="width: {(count / statsCategoriesMax) * 100}%"
                      ></span>
                    </span>
                    <span class="text-sm text-dark-grey font-bold tabular-nums">{count}</span>
                  </li>
                {/each}
              </ul>
            {/if}

            <h3 class="text-sm mb-1! text-dark-grey font-bold">
              {m['admin.promptChecks.stats.warningsTitle']()}
            </h3>
            <p class="text-sm mb-1!" id="prompt-check-stats-warnings">
              {m['admin.promptChecks.stats.warningsShown']({ count: stats.warnings_shown })}, {m[
                'admin.promptChecks.stats.proceeded'
              ]({ count: stats.proceeded })}
            </p>
            <p class="fr-hint-text mt-0!">{m['admin.promptChecks.stats.warningsHint']()}</p>
          </div>
        </div>
      {/if}
    </section>
  </div>
</PageLayout>

<style lang="postcss">
  .action-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
    margin: 0;
    padding: 0;
    border: 0;
  }

  .action-pills label {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.25rem 0.625rem;
    border: 1px solid var(--border-default-grey);
    border-radius: 999px;
    background: var(--background-default-grey);
    color: var(--text-mention-grey);
    font-size: 0.8125rem;
    line-height: 1.5;
    white-space: nowrap;
    cursor: pointer;
  }

  .action-pills label:hover {
    background: var(--background-default-grey-hover);
    color: var(--text-default-grey);
  }

  .action-pills input:checked + label {
    border-color: var(--pill-color);
    box-shadow: inset 0 0 0 1px var(--pill-color);
    background: var(--pill-soft);
    color: var(--text-default-grey);
    font-weight: 700;
  }

  .action-pills input:checked + label :global(.pill-icon),
  .action-pills label:hover :global(.pill-icon) {
    color: var(--pill-color);
  }

  .action-pills input:focus-visible + label {
    outline: 2px solid var(--outline-color);
    outline-offset: 2px;
  }

  .action-pills input:disabled + label {
    cursor: not-allowed;
    opacity: 0.6;
  }
</style>
