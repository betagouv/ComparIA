<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Alert, Button, Icon, Select, Textarea } from '$components/dsfr'
  import {
    FormInput,
    FormSecretInput,
    type FormFieldsetItemProps,
    type FormInputProps
  } from '$components/form'
  import Form from '$components/form/Form.svelte'
  import { PageLayout } from '$components/layout'
  import { promptCheckMessage } from '$lib/apiErrors'
  import { api } from '$lib/fastapi-client'
  import type { PromptCheckCriterion, PromptCheckStatus } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import { useForm } from '$lib/stores/form.svelte'
  import type { AnyFormItemProps } from '$lib/utils/form'
  import type { PageProps } from './$types'
  import ActivityLineChart from './ActivityLineChart.svelte'
  import CriterionHistogram from './CriterionHistogram.svelte'
  import CriterionRow, { actionTone } from './CriterionRow.svelte'
  import { actionLabels, actionOrder, newCriterion } from './criteria'
  import type { PromptCheckDecision, PromptCheckStats, PromptCheckTry } from './types'

  let { data }: PageProps = $props()

  const form = $derived(
    useForm({
      url: '/admin/prompt-check',
      // The key is write-only: it is in the form, never in what the API returns.
      data: data.check as PromptCheckStatus & { api_key?: string },
      schema: data.schema,
      i18nKey: 'prompt_check_upsert',
      method: 'put',
      omitKeys: [
        'has_api_key',
        'updated_at',
        'updated_by',
        'consecutive_failures',
        'key_rejected',
        'out_of_credits',
        'no_api_key',
        'no_model',
        'healthy',
        'warnings_shown',
        'default_conversations_per_ip_per_hour',
        'default_conversations_same_models_per_ip_per_hour'
      ],
      onSuccess: () => invalidate('admin:prompt-check')
    })
  )

  const field = (id: string) => form.items.find((item) => item.id === id)!
  // The schema describes a criterion as a fieldset: its fields give the labels and help.
  const criterionFields = $derived(
    Object.fromEntries(
      (field('criteria') as unknown as { subProps: FormFieldsetItemProps }).subProps.subProps.map(
        (item: AnyFormItemProps) => [item.id, item]
      )
    )
  )
  const savedKeys = $derived(data.check.criteria.map((criterion) => criterion.key))
  const criteria = $derived((form.form.criteria ?? []) as PromptCheckCriterion[])

  const decisionTone: Record<PromptCheckDecision, string> = {
    pass: 'var(--green-emeraude-main-632)',
    logged: 'var(--info-425-625)',
    warned: 'var(--yellow-tournesol-main-731)',
    blocked: 'var(--error-425-625)',
    error: 'var(--purple-glycine-main-494)',
    skipped: 'var(--grey-425-625)'
  }
  const decisionLabels: Record<PromptCheckDecision, string> = {
    pass: m['admin.promptChecks.bench.decision.pass'](),
    logged: m['admin.promptChecks.bench.decision.logged'](),
    warned: m['admin.promptChecks.bench.decision.warned'](),
    blocked: m['admin.promptChecks.bench.decision.blocked'](),
    error: m['admin.promptChecks.bench.decision.error'](),
    skipped: m['admin.promptChecks.bench.decision.skipped']()
  }
  const statsDecisionLabels: Record<PromptCheckDecision, string> = {
    pass: m['admin.promptChecks.stats.decision.pass'](),
    logged: m['admin.promptChecks.stats.decision.logged'](),
    warned: m['admin.promptChecks.stats.decision.warned'](),
    blocked: m['admin.promptChecks.stats.decision.blocked'](),
    error: m['admin.promptChecks.stats.decision.error'](),
    skipped: m['admin.promptChecks.stats.decision.skipped']()
  }
  const decisionOrder: PromptCheckDecision[] = [
    'pass',
    'logged',
    'warned',
    'blocked',
    'error',
    'skipped'
  ]

  let benchText = $state('')
  let benchRunning = $state(false)
  let benchError = $state('')
  let benchResult = $state<PromptCheckTry | null>(null)
  // Figé au moment du test : la personne peut modifier les réglages ensuite,
  // le panneau doit rester le compte rendu de ce qui a réellement été essayé.
  let benchUsed = $state<PromptCheckCriterion[]>([])

  const benchRows = $derived.by(() => {
    const result = benchResult
    if (!result) return []
    // Criteria set to off are not asked, so they have no score.
    return benchUsed
      .filter((criterion) => criterion.key in result.scores)
      .map((criterion) => ({
        key: criterion.key,
        label: criterion.label,
        score: result.scores[criterion.key],
        threshold: criterion.threshold,
        action: criterion.action,
        triggered: criterion.key in result.triggered
      }))
  })

  function benchMessage(result: PromptCheckTry): string {
    if (result.decision === 'error') {
      if (result.message === 'no_model') return m['admin.promptChecks.bench.errors.no_model']()
      if (result.message === 'no_api_key') return m['admin.promptChecks.bench.errors.no_api_key']()
      return m['admin.promptChecks.bench.errors.call_failed']({ error: result.error ?? '' })
    }
    if (!result.message) return m['admin.promptChecks.bench.messageNone']()
    return promptCheckMessage(result.message)
  }

  async function runBench() {
    const text = benchText.trim()
    if (text === '') {
      benchResult = null
      benchError = m['admin.promptChecks.bench.empty']()
      return
    }

    benchRunning = true
    benchError = ''
    try {
      const used = $state.snapshot(criteria)
      benchResult = await api.request<PromptCheckTry>('/admin/prompt-check/try', {
        method: 'POST',
        body: JSON.stringify({
          text,
          criteria: used,
          description: form.form.description,
          model: form.form.model
        })
      })
      benchUsed = used
    } catch (error) {
      benchResult = null
      benchError = (error as Error).message
    } finally {
      benchRunning = false
    }
  }

  /** The stats keep the keys of the old Mistral categories: with no label, the key shows. */
  function criterionLabel(key: string) {
    return data.check.criteria.find((criterion) => criterion.key === key)?.label ?? key
  }

  function formatScore(value: number) {
    // Trois décimales, jamais arrondi à la première : 0,410 contre un seuil de
    // 0,500 est justement ce qu'un administrateur vient regarder ici.
    return value.toFixed(3).replace('.', ',')
  }

  function percent(value: number) {
    return Math.min(100, Math.max(0, value * 100))
  }

  type StatsPeriod = PromptCheckStats['period']
  // svelte-ignore state_referenced_locally
  let stats = $state<PromptCheckStats | null>(data.stats ?? null)
  let statsPeriod = $state<StatsPeriod>('all')
  let statsLoading = $state(false)
  const periodOptions: { value: StatsPeriod; label: string }[] = [
    { value: 'all', label: m['admin.promptChecks.stats.periods.all']() },
    { value: '7d', label: m['admin.promptChecks.stats.periods.7d']() },
    { value: '30d', label: m['admin.promptChecks.stats.periods.30d']() },
    { value: '90d', label: m['admin.promptChecks.stats.periods.90d']() },
    { value: '365d', label: m['admin.promptChecks.stats.periods.365d']() }
  ]

  async function loadStats(period: StatsPeriod) {
    statsLoading = true
    try {
      stats = await api.request<PromptCheckStats>('/admin/prompt-check/stats', {
        searchParams: { period }
      })
    } finally {
      statsLoading = false
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
  <div class="gap-8 mx-auto flex max-w-[1120px] flex-col">
    <section id="prompt-check-health-band" class="empty:hidden">
      {#if data.check.enabled && data.check.no_model}
        <Alert variant="warning" title={m['admin.promptChecks.health.noModel']()}>
          <p>{m['admin.promptChecks.health.noModelHint']()}</p>
        </Alert>
      {:else if data.check.enabled && data.check.no_api_key}
        <Alert variant="warning" title={m['admin.promptChecks.health.noKey']()}>
          <p>{m['admin.promptChecks.health.noKeyHint']()}</p>
        </Alert>
      {:else if data.check.key_rejected}
        <Alert variant="error" title={m['admin.promptChecks.health.keyRejected']()}>
          <p>
            {data.check.required
              ? m['admin.promptChecks.health.keyRejectedHint']()
              : m['admin.promptChecks.health.keyRejectedHintOptional']()}
          </p>
        </Alert>
      {:else if data.check.out_of_credits}
        <Alert variant="error" title={m['admin.promptChecks.health.noCredits']()}>
          <p>
            {data.check.required
              ? m['admin.promptChecks.health.noCreditsHint']()
              : m['admin.promptChecks.health.noCreditsHintOptional']()}
          </p>
        </Alert>
      {:else if data.check.healthy === false}
        <Alert variant="error" title={m['admin.promptChecks.health.unhealthy']()}>
          <p>
            {data.check.required
              ? m['admin.promptChecks.health.unhealthyHint']()
              : m['admin.promptChecks.health.unhealthyHintOptional']()}
          </p>
          <p>
            {m['admin.promptChecks.health.failures']({
              count: data.check.consecutive_failures ?? 0
            })}
          </p>
        </Alert>
      {/if}
    </section>

    {#snippet model()}
      <FormInput
        {...field('model') as FormInputProps}
        list="prompt-check-model-options"
        bind:value={form.form.model!}
      />
      <datalist id="prompt-check-model-options">
        {#each data.models as option (option.id)}
          <option value={option.id}>{option.name}</option>
        {/each}
      </datalist>
    {/snippet}

    {#snippet apiKey()}
      <FormSecretInput
        {...field('api_key') as FormInputProps}
        stored={data.check.has_api_key}
        removeUrl="/admin/prompt-check/api-key"
        removedMessage={m['admin.promptChecks.apiKey.removed']()}
        removeId="prompt-check-api-key-remove"
        onremoved={() => invalidate('admin:prompt-check')}
        bind:value={form.form.api_key!}
      />
    {/snippet}

    {#snippet description()}
      <Textarea
        id="description"
        label={field('description').label}
        help={field('description').help}
        error={form.errors['description']}
        rows={3}
        maxlength={data.schema.properties?.description?.maxLength}
        bind:value={form.form.description!}
      />
    {/snippet}

    {#snippet criteriaList()}
      <!-- min-w-0: a fieldset is as wide as its content by default, and the
           action pills pushed it past the edge of the form. -->
      <fieldset id="criteria" class="fr-fieldset min-w-0">
        <legend class="fr-fieldset__legend">{field('criteria').label}</legend>
        <div class="mb-4 p-4 cg-border w-full bg-[--cg-very-light-grey]">
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
                  {m[`admin.promptChecks.actions.help.${action}`]()}
                </span>
              </li>
            {/each}
          </ul>
        </div>
        <ul class="m-0! p-0! w-full list-none">
          {#each criteria as criterion, i (i)}
            <CriterionRow
              id="criteria-{i}"
              bind:criterion={criteria[i]}
              fields={criterionFields}
              saved={savedKeys.includes(criterion.key)}
              takenKeys={criteria.filter((_, j) => j !== i).map((other) => other.key)}
              errors={form.errors}
              onremove={() => (form.form.criteria = criteria.filter((_, j) => j !== i))}
            />
          {:else}
            <p id="prompt-check-criteria-empty" class="text-sm text-grey">
              {m['admin.promptChecks.criteria.empty']()}
            </p>
          {/each}
        </ul>
        <Button
          id="prompt-check-criteria-add"
          variant="secondary"
          icon="add-line"
          text={m['admin.promptChecks.criteria.add']()}
          onclick={() => (form.form.criteria = [...criteria, newCriterion()])}
          class="mt-4"
        />
      </fieldset>
    {/snippet}

    {#snippet capPerIp()}
      <FormInput
        {...field('conversations_per_ip_per_hour') as FormInputProps}
        placeholder={String(data.check.default_conversations_per_ip_per_hour)}
        bind:value={form.form.conversations_per_ip_per_hour!}
      />
    {/snippet}

    {#snippet capSameModels()}
      <FormInput
        {...field('conversations_same_models_per_ip_per_hour') as FormInputProps}
        placeholder={String(data.check.default_conversations_same_models_per_ip_per_hour)}
        bind:value={form.form.conversations_same_models_per_ip_per_hour!}
      />
    {/snippet}

    <Form
      id="prompt-check-form"
      label={m['admin.promptChecks.settings.title']()}
      {...form}
      fieldSnippets={{
        model,
        api_key: apiKey,
        description,
        criteria: criteriaList,
        conversations_per_ip_per_hour: capPerIp,
        conversations_same_models_per_ip_per_hour: capSameModels
      }}
    />

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
              aria-describedby="prompt-check-bench-messages"></textarea>
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
              {benchMessage(benchResult)}
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
              {#each benchRows as row (row.key)}
                {@const tone = row.triggered ? actionTone[row.action].color : 'var(--grey-425-625)'}
                <li id={`prompt-check-bench-row-${row.key}`}>
                  <div class="gap-2 mb-1 flex flex-wrap items-baseline">
                    <span class="text-sm text-dark-grey min-w-0 font-medium flex-1"
                      >{row.label}</span
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
          <h2 class="fr-h5 mb-1!">{m['admin.promptChecks.stats.title']()}</h2>
          <p class="text-sm mb-0! text-grey">{m['admin.promptChecks.stats.subtitle']()}</p>
        </div>
        <Select
          id="prompt-check-stats-period"
          label={m['admin.promptChecks.stats.periodLabel']()}
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
            <p class="mb-0! text-sm text-grey">{m['admin.promptChecks.stats.totalLabel']()}</p>
          </div>

          <div class="cg-border bg-white p-5">
            <div class="gap-3 mb-4 flex flex-wrap items-baseline justify-between">
              <div>
                <h3 class="fr-h6 mb-1!">{m['admin.promptChecks.stats.timelineTitle']()}</h3>
                <p class="text-sm mb-0! text-grey">
                  {m['admin.promptChecks.stats.timelineHint']()}
                </p>
              </div>
              <p class="text-sm mb-0! text-grey">
                {m['admin.promptChecks.stats.checked']({ count: stats.total })}
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
              <h3 class="fr-h6 mb-1!">{m['admin.promptChecks.stats.byCriterionTitle']()}</h3>
              <p class="text-sm mt-0! mb-4! text-grey">
                {m['admin.promptChecks.stats.byCriterionHint']()}
              </p>
              <CriterionHistogram
                byCriterion={stats.by_criterion}
                {criterionLabel}
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
  /* Same tint as the FormInput fields of the form. */
  :global(#prompt-check-form textarea.fr-input) {
    --border-plain-grey: var(--blue-france-main-525);
    --background-contrast-grey: var(--blue-ecume-975-75);
  }

  .historical-kpi {
    border-left: 4px solid var(--brand-primary);
  }

  .result-card {
    border: 1px solid color-mix(in srgb, var(--result-tone) 24%, var(--border-default-grey));
    background: color-mix(in srgb, var(--result-tone) 7%, var(--background-default-grey));
  }
</style>
