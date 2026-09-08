<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Alert, Button, Icon, Select, Toggle } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import type { PromptCheckPatch, PromptCheckStatus } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { tick } from 'svelte'
  import type { PageProps } from './$types'
  import ActivityLineChart from './ActivityLineChart.svelte'
  import CategoryHistogram from './CategoryHistogram.svelte'
  import type { PromptCheckDecision, PromptCheckStats, PromptCheckTry } from './types'

  type Action = 'off' | 'log' | 'warn' | 'block'
  type Saving = 'enabled' | 'model' | 'apiKey' | 'categories'
  type CategoryConfig = { threshold: number; action: Action }
  type DraftRow = { threshold: string | number; action: Action }
  type Draft = { enabled: boolean; model: string; categories: Record<string, DraftRow> }

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
  let saving = $state<Saving | null>(null)
  let errors = $state<Record<string, string>>({})

  // La clé n'est jamais renvoyée au navigateur. Quand une clé est en place, le
  // champ laisse la place à des points : de la décoration, pas la valeur, dont
  // la longueur n'a rien à voir avec celle de la clé.
  const maskedKey = '•'.repeat(12)
  let apiKey = $state('')
  // svelte-ignore state_referenced_locally
  let editingApiKey = $state(!data.check.has_api_key)
  let apiKeyField = $state<HTMLInputElement | null>(null)

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
    apiKey = ''
    editingApiKey = !data.check.has_api_key
  })

  const failures = $derived(data.check.consecutive_failures ?? 0)
  const modelChanged = $derived(draft.model.trim() !== data.check.model)
  const categories = $derived(categoryOrder.filter((category) => category in data.check.categories))

  const decisionOrder: PromptCheckDecision[] = ['pass', 'logged', 'warned', 'blocked', 'error']
  type StatsPeriod = PromptCheckStats['period']
  // svelte-ignore state_referenced_locally
  let stats = $state<PromptCheckStats | null>(data.stats ?? null)
  let statsPeriod = $state<StatsPeriod>('all')
  let statsLoading = $state(false)
  const periodOptions: { value: StatsPeriod; label: string }[] = [
    { value: 'all', label: 'Depuis le début' },
    { value: '7d', label: '7 derniers jours' },
    { value: '30d', label: '30 derniers jours' },
    { value: '90d', label: '90 derniers jours' },
    { value: '365d', label: '12 derniers mois' }
  ]

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
      enabled: check.enabled,
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

  async function loadStats(period: StatsPeriod) {
    statsLoading = true
    try {
      stats = await api.request<PromptCheckStats>(`/admin/prompt-check/stats?period=${period}`)
    } finally {
      statsLoading = false
    }
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

  /** Chaque enregistrement n'envoie que ses propres champs. */
  async function patch(kind: Saving, body: PromptCheckPatch) {
    saving = kind
    try {
      await api.request<PromptCheckStatus>('/admin/prompt-check', {
        method: 'PATCH',
        body: JSON.stringify(body)
      })
      useToast(m['admin.promptChecks.saved'](), 4000)
      await invalidate('admin:prompt-check')
      return true
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
      return false
    } finally {
      saving = null
    }
  }

  async function saveEnabled() {
    const wanted = draft.enabled
    const done = await patch('enabled', { enabled: wanted })
    // Un interrupteur qui reste sur une position qu'il n'a pas obtenue ment.
    if (!done) draft.enabled = !wanted
  }

  async function saveModel(event: SubmitEvent) {
    event.preventDefault()
    if (!modelChanged) return
    await patch('model', { model: draft.model.trim() })
  }

  async function saveApiKey(event: SubmitEvent) {
    event.preventDefault()
    await patch('apiKey', { api_key: apiKey.trim() })
  }

  async function replaceApiKey() {
    editingApiKey = true
    await tick()
    apiKeyField?.focus()
  }

  async function saveCategories(event: SubmitEvent) {
    event.preventDefault()

    const { categories, fieldErrors } = readDraft()
    errors = fieldErrors
    if (Object.keys(fieldErrors).length > 0) return

    await patch('categories', {
      categories: categories as unknown as PromptCheckPatch['categories']
    })
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
  <div class="gap-8 mx-auto flex max-w-[1120px] flex-col">
    <section id="prompt-check-health-band" class="empty:hidden">
      {#if data.check.healthy === false}
        <Alert variant="error" title={m['admin.promptChecks.health.unhealthy']()} class="mb-6">
          <p>{m['admin.promptChecks.health.unhealthyHint']()}</p>
          <p>{m['admin.promptChecks.health.failures']({ count: failures })}</p>
        </Alert>
      {/if}
    </section>

    <div id="prompt-check-settings" class="settings-panel p-4 md:p-5">
      <h2 class="fr-h6 gap-2 mb-4! text-dark-grey flex items-center">
        <Icon
          icon="i-ri-shield-check-line"
          size="sm"
          class="text-primary shrink-0"
          aria-hidden="true"
        />
        {m['admin.promptChecks.settings.title']()}
      </h2>

      <div class="settings-switch pb-4" onchange={saveEnabled}>
        <Toggle
          id="prompt-check-enabled"
          bind:value={draft.enabled}
          label={m['admin.promptChecks.settings.enabled']()}
          hideCheckLabel
          class="mb-0! pr-13! text-dark-grey font-medium"
        />
      </div>

      <div class="gap-x-5 gap-y-4 md:grid-cols-2 mt-4 grid items-start">
        <form id="prompt-check-model-form" onsubmit={saveModel}>
          <label
            class="fr-label mt-0! mb-1! text-sm text-dark-grey font-medium"
            for="prompt-check-model"
          >
            {m['admin.promptChecks.model.label']()}
          </label>
          <div class="gap-2 flex flex-wrap items-start">
            <input
              id="prompt-check-model"
              class="fr-input min-w-[12rem] flex-1"
              bind:value={draft.model}
              disabled={saving === 'model'}
            />
            <Button
              id="prompt-check-model-save"
              type="submit"
              variant="secondary"
              text={saving === 'model'
                ? m['admin.promptChecks.saving']()
                : m['admin.promptChecks.saveModel']()}
              disabled={saving === 'model' || !modelChanged}
            />
          </div>
        </form>

        <form id="prompt-check-api-key-form" onsubmit={saveApiKey}>
          <div class="gap-2 mb-1 flex flex-wrap items-baseline justify-between">
            {#if editingApiKey}
              <label
                class="fr-label mt-0! mb-0! text-sm text-dark-grey font-medium"
                for="prompt-check-api-key"
              >
                {m['admin.promptChecks.apiKey.label']()}
              </label>
            {:else}
              <span class="fr-label mt-0! mb-0! text-sm text-dark-grey font-medium">
                {m['admin.promptChecks.apiKey.label']()}
              </span>
            {/if}
            <span id="prompt-check-api-key-state" class="text-xs text-grey">
              {data.check.has_api_key
                ? m['admin.promptChecks.apiKey.set']()
                : m['admin.promptChecks.apiKey.unset']()}
            </span>
          </div>

          {#if editingApiKey}
            <div class="gap-2 flex flex-wrap items-start">
              <input
                id="prompt-check-api-key"
                class="fr-input min-w-[12rem] flex-1"
                type="password"
                autocomplete="off"
                placeholder={m['admin.promptChecks.apiKey.placeholder']()}
                bind:value={apiKey}
                bind:this={apiKeyField}
                disabled={saving === 'apiKey'}
              />
              <Button
                id="prompt-check-api-key-save"
                type="submit"
                variant="secondary"
                text={saving === 'apiKey'
                  ? m['admin.promptChecks.saving']()
                  : m['admin.promptChecks.saveApiKey']()}
                disabled={saving === 'apiKey' || apiKey.trim() === ''}
              />
            </div>
          {:else}
            <div class="gap-2 flex flex-wrap items-center">
              <button
                id="prompt-check-api-key-masked"
                type="button"
                class="fr-input mb-0! min-w-[12rem] flex-1 cursor-text text-left tracking-[0.25em] select-none"
                aria-label="Remplacer la clé API"
                onclick={replaceApiKey}
              >
                {maskedKey}
              </button>
              <Button
                id="prompt-check-api-key-replace"
                variant="secondary"
                text={m['admin.promptChecks.apiKey.replace']()}
                onclick={replaceApiKey}
              />
            </div>
          {/if}
        </form>
      </div>
    </div>

    <form id="prompt-check-categories-form" onsubmit={saveCategories}>
      <h2 class="fr-h5 mb-3!">{m['admin.promptChecks.categoriesTitle']()}</h2>

      {#if !draft.enabled}
        <p id="prompt-check-disabled-notice" class="mb-3! text-sm text-grey">
          {m['admin.promptChecks.settings.disabledNotice']()}
        </p>
      {/if}

      <div
        class={[
          'mb-5 cg-border p-3 md:p-4 bg-[--cg-very-light-grey]',
          { 'opacity-60': !draft.enabled }
        ]}
      >
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
        class={['m-0! p-0! flex list-none flex-col', { 'opacity-60': !draft.enabled }]}
        aria-label={m['admin.promptChecks.categoriesTitle']()}
      >
        {#each categories as category (category)}
          <li
            id={`prompt-check-row-${category}`}
            class={[
              'gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center px-1 py-3 grid',
              'border-0 border-b border-solid border-[--border-default-grey] last:border-b-0'
            ]}
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
                    disabled={saving === 'categories'}
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
                    disabled={saving === 'categories'}
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

      <Button
        id="prompt-check-categories-save"
        type="submit"
        text={saving === 'categories'
          ? m['admin.promptChecks.saving']()
          : m['admin.promptChecks.saveCategories']()}
        disabled={saving === 'categories'}
        class="mt-4"
      />
    </form>

    <section id="prompt-check-bench">
      <h2 class="fr-h5 mb-1!">{m['admin.promptChecks.bench.title']()}</h2>

      <div class="gap-6 flex flex-col">
        <div>
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
      <div class="gap-4 mb-5 flex flex-wrap items-end justify-between">
        <div>
          <h2 class="fr-h5 mb-1!">Activité des messages</h2>
          <p class="text-sm mb-0! text-grey">
            Suivez les détections et les décisions prises sur la période sélectionnée.
          </p>
        </div>
        <Select
          id="prompt-check-stats-period"
          label="Période affichée"
          bind:selected={statsPeriod}
          options={periodOptions}
          groupClass="mb-0! min-w-[220px]"
          disabled={statsLoading}
          onchange={() => loadStats(statsPeriod)}
        />
      </div>
      {#if !stats}
        <p class="text-sm text-grey">
          {m['admin.promptChecks.stats.unavailable']()}
        </p>
      {:else}
        <div class="gap-5 flex flex-col" class:opacity-60={statsLoading} aria-busy={statsLoading}>
          <div class="cg-border historical-kpi bg-white p-5">
            <p class="text-xs mb-2! text-grey font-medium tracking-wide uppercase">
              {periodOptions.find((option) => option.value === statsPeriod)?.label}
            </p>
            <p id="prompt-check-stats-total" class="mb-1! text-dark-grey text-5xl font-bold">
              {stats.total}
            </p>
            <p class="mb-0! text-sm text-grey">messages vérifiés sur la période</p>
          </div>

          <div class="cg-border bg-white p-5">
            <div class="gap-3 mb-4 flex flex-wrap items-baseline justify-between">
              <div>
                <h3 class="fr-h6 mb-1!">Détections dans le temps</h3>
                <p class="text-sm mb-0! text-grey">
                  Messages surveillés, prévenus, refusés ou en échec sur la période.
                </p>
              </div>
              <p class="text-sm mb-0! text-grey">
                <strong class="text-dark-grey">{stats.total}</strong> messages vérifiés
              </p>
            </div>
            <ActivityLineChart
              points={stats.timeline}
              labels={statsDecisionLabels}
              colors={decisionTone}
            />
          </div>

          <div class="gap-5 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] grid items-start">
            <div class="cg-border bg-white p-5">
              <h3 class="fr-h6 mb-3!">{m['admin.promptChecks.stats.byDecisionTitle']()}</h3>
              <div class="gap-2 sm:grid-cols-2 grid grid-cols-1">
                {#each decisionOrder as decision (decision)}
                  <div
                    id={`prompt-check-stats-decision-${decision}`}
                    class="result-card p-3 rounded-lg"
                    style="--result-tone: {decisionTone[decision]}"
                  >
                    <p class="gap-2 mb-2! text-xs text-grey flex items-center">
                      {@render statusDot(decisionTone[decision])}
                      {statsDecisionLabels[decision]}
                    </p>
                    <p class="mb-0! text-dark-grey text-2xl font-bold leading-none">
                      {stats.by_decision[decision] ?? 0}
                    </p>
                  </div>
                {/each}
              </div>
            </div>

            <div class="cg-border bg-white p-5">
              <h3 class="fr-h6 mb-1!">{m['admin.promptChecks.stats.byCategoryTitle']()}</h3>
              <p class="text-sm mt-0! mb-4! text-grey">
                Répartition des détections par catégorie et par résultat.
              </p>
              <CategoryHistogram
                categories={stats.by_category}
                {categoryLabel}
                labels={statsDecisionLabels}
                colors={decisionTone}
              />
            </div>
          </div>
        </div>
      {/if}
    </section>
  </div>
</PageLayout>

<style lang="postcss">
  .historical-kpi {
    border-left: 4px solid var(--brand-primary);
    background: linear-gradient(
      110deg,
      color-mix(in srgb, var(--brand-primary) 8%, var(--background-default-grey)),
      var(--background-default-grey) 65%
    );
  }

  .result-card {
    border: 1px solid color-mix(in srgb, var(--result-tone) 24%, var(--border-default-grey));
    background: color-mix(in srgb, var(--result-tone) 7%, var(--background-default-grey));
  }

  /* Même traitement que le panneau .iasummit de l'arène : un dégradé de marque
     très doux, repris ici avec les jetons de thème pour suivre le mode sombre. */
  .settings-panel {
    border: 1px solid color-mix(in srgb, var(--brand-primary) 22%, transparent);
    border-radius: 0.75rem;
    background: linear-gradient(
      57deg,
      color-mix(in srgb, var(--brand-primary) 13%, var(--background-default-grey)) 8.29%,
      color-mix(in srgb, var(--brand-primary) 5%, var(--background-default-grey)) 36.19%,
      var(--background-default-grey) 96.89%
    );
  }

  :root[data-fr-theme='dark'] .settings-panel {
    border-color: color-mix(in srgb, var(--brand-primary) 30%, transparent);
    background: linear-gradient(
      57deg,
      color-mix(in srgb, var(--brand-primary) 16%, var(--background-default-grey)) 8.29%,
      color-mix(in srgb, var(--brand-primary) 7%, var(--background-default-grey)) 36.19%,
      var(--background-default-grey) 96.89%
    );
  }

  .settings-switch {
    border-bottom: 1px solid color-mix(in srgb, var(--brand-primary) 18%, transparent);
  }

  :root[data-fr-theme='dark'] .settings-switch {
    border-bottom-color: color-mix(in srgb, var(--brand-primary) 26%, transparent);
  }

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
