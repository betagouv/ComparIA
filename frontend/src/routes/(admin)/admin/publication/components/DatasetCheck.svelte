<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Alert, Button, Textarea } from '$components/dsfr'
  import {
    FormInput,
    FormSecretInput,
    FormSelect,
    type FormFieldsetItemProps,
    type FormInputProps
  } from '$components/form'
  import Form from '$components/form/Form.svelte'
  import { api } from '$lib/fastapi-client'
  import type {
    DatasetCheckCriterion,
    DatasetCheckPublic,
    DatasetCheckTryResult
  } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import { useForm } from '$lib/stores/form.svelte'
  import type { AnyFormItemProps, JSONSchema } from '$lib/utils/form'
  import CriterionRow from '$components/admin/CriterionRow.svelte'
  import type { PromptCheckModel } from '../../prompt-checks/types'

  let {
    check,
    schema,
    models
  }: { check: DatasetCheckPublic; schema: JSONSchema; models: PromptCheckModel[] } = $props()

  const refetch = () => invalidate('admin:publishing')

  const form = $derived(
    useForm({
      url: '/admin/dataset-check',
      // The key is write-only: it is in the form, never in what the API returns.
      data: check as DatasetCheckPublic & { api_key?: string },
      schema,
      i18nKey: 'dataset_check_upsert',
      method: 'put',
      omitKeys: ['has_api_key', 'updated_at', 'updated_by', 'no_api_key', 'no_model'],
      onSuccess: refetch
    })
  )

  const field = (id: string) => form.items.find((item) => item.id === id)!
  const criterionFields = $derived(
    Object.fromEntries(
      (field('criteria') as unknown as { subProps: FormFieldsetItemProps }).subProps.subProps.map(
        (item: AnyFormItemProps) => [item.id, item]
      )
    )
  )
  const savedKeys = $derived(check.criteria.map((criterion) => criterion.key))
  const criteria = $derived((form.form.criteria ?? []) as DatasetCheckCriterion[])

  const reasonLabels = {
    pii: m['admin.publishing.datasetCheck.reasons.pii'](),
    spam: m['admin.publishing.datasetCheck.reasons.spam']()
  }
  const reasonOptions = Object.entries(reasonLabels).map(([value, label]) => ({ value, label }))

  function newCriterion(): DatasetCheckCriterion {
    return { key: '', label: '', question: '', yes: '', no: '', threshold: 0.3, reason: 'spam' }
  }

  let tryText = $state('')
  let tryRunning = $state(false)
  let tryError = $state('')
  let tryResult = $state<DatasetCheckTryResult | null>(null)
  // Frozen when the test runs, so editing the settings afterwards does not
  // change what the result says was tried.
  let tryCriteria = $state<DatasetCheckCriterion[]>([])

  async function runTry() {
    const text = tryText.trim()
    if (!text) {
      tryResult = null
      tryError = m['admin.publishing.datasetCheck.try.empty']()
      return
    }
    tryRunning = true
    tryError = ''
    try {
      const used = $state.snapshot(criteria)
      tryResult = await api.request<DatasetCheckTryResult>('/admin/dataset-check/try', {
        method: 'POST',
        body: JSON.stringify({
          text,
          model: form.form.model || undefined,
          description: form.form.description,
          criteria: used,
          category_threshold: form.form.category_threshold,
          language_threshold: form.form.language_threshold
        })
      })
      tryCriteria = used
    } catch (error) {
      tryResult = null
      tryError = (error as Error).message
    } finally {
      tryRunning = false
    }
  }

  function tryMessage(result: DatasetCheckTryResult) {
    if (result.message === 'no_model') return m['admin.promptChecks.bench.errors.no_model']()
    if (result.message === 'no_api_key') return m['admin.promptChecks.bench.errors.no_api_key']()
    return m['admin.promptChecks.bench.errors.call_failed']({ error: result.error ?? '' })
  }

  const formatScore = (value: number) => value.toFixed(3).replace('.', ',')
</script>

<div class="gap-6 flex flex-col">
  {#if check.no_model}
    <Alert variant="warning" title={m['admin.publishing.datasetCheck.noModel']()}>
      <p>{m['admin.publishing.datasetCheck.noModelHint']()}</p>
    </Alert>
  {:else if check.no_api_key}
    <Alert variant="warning" title={m['admin.publishing.datasetCheck.noKey']()}>
      <p>{m['admin.publishing.datasetCheck.noKeyHint']()}</p>
    </Alert>
  {/if}

  {#snippet model()}
    <FormInput
      {...field('model') as FormInputProps}
      list="dataset-check-model-options"
      bind:value={form.form.model!}
    />
    <datalist id="dataset-check-model-options">
      {#each models as option (option.id)}
        <option value={option.id}>{option.name}</option>
      {/each}
    </datalist>
  {/snippet}

  {#snippet apiKey()}
    <FormSecretInput
      {...field('api_key') as FormInputProps}
      stored={check.has_api_key}
      removeUrl="/admin/dataset-check/api-key"
      removedMessage={m['admin.promptChecks.apiKey.removed']()}
      removeId="dataset-check-api-key-remove"
      onremoved={refetch}
      bind:value={form.form.api_key!}
    />
  {/snippet}

  {#snippet description()}
    <Textarea
      id="dataset-check-description"
      label={field('description').label}
      help={field('description').help}
      error={form.errors['description']}
      rows={3}
      maxlength={schema.properties?.description?.maxLength}
      bind:value={form.form.description!}
    />
  {/snippet}

  {#snippet criteriaList()}
    <fieldset id="criteria" class="fr-fieldset min-w-0">
      <legend class="fr-fieldset__legend">
        {field('criteria').label}
        <span class="fr-hint-text">{field('criteria').help}</span>
      </legend>
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
          >
            {#snippet tag()}
              <!-- The name says it already: on a phone it needs the room. -->
              <span class="max-sm:hidden">{reasonLabels[criterion.reason ?? 'spam']}</span>
            {/snippet}
            {#snippet settings()}
              <div class="gap-x-4 md:grid-cols-2 grid">
                <FormInput
                  {...criterionFields.threshold as FormInputProps}
                  id="criteria-{i}-threshold"
                  type="number"
                  step="0.05"
                  errors={form.errors}
                  bind:value={criteria[i].threshold}
                />
                <FormSelect
                  {...criterionFields.reason}
                  id="criteria-{i}-reason"
                  component="select"
                  options={reasonOptions}
                  errors={form.errors}
                  bind:value={criteria[i].reason as string}
                />
              </div>
            {/snippet}
          </CriterionRow>
        {:else}
          <p id="dataset-check-criteria-empty" class="text-sm text-grey">
            {m['admin.publishing.datasetCheck.criteriaEmpty']()}
          </p>
        {/each}
      </ul>
      <Button
        id="dataset-check-criteria-add"
        variant="secondary"
        icon="add-line"
        text={m['admin.promptChecks.criteria.add']()}
        onclick={() => (form.form.criteria = [...criteria, newCriterion()])}
        class="mt-4"
      />
    </fieldset>
  {/snippet}

  <Form
    id="dataset-check-form"
    class="mt-0! max-w-none"
    label={m['admin.publishing.datasetCheck.formTitle']()}
    {...form}
    fieldSnippets={{ model, api_key: apiKey, description, criteria: criteriaList }}
  />

  <section id="dataset-check-try" class="p-6 cg-border">
    <h3 class="fr-h6 mb-1!">{m['admin.publishing.datasetCheck.try.title']()}</h3>
    <div class={['fr-input-group', { 'fr-input-group--error': !!tryError }]}>
      <label class="fr-label" for="dataset-check-try-text">
        {m['admin.publishing.datasetCheck.try.label']()}
        <span class="fr-hint-text">{m['admin.publishing.datasetCheck.try.hint']()}</span>
      </label>
      <textarea
        id="dataset-check-try-text"
        class="fr-input"
        rows="6"
        bind:value={tryText}
        disabled={tryRunning}></textarea>
      {#if tryError}
        <p class="fr-message fr-message--error" aria-live="polite">{tryError}</p>
      {/if}
    </div>
    <Button
      id="dataset-check-try-run"
      variant="secondary"
      onclick={runTry}
      text={tryRunning
        ? m['admin.promptChecks.bench.running']()
        : m['admin.publishing.datasetCheck.try.run']()}
      disabled={tryRunning}
    />

    {#if tryResult}
      <div id="dataset-check-try-result" class="mt-6" aria-live="polite">
        {#if tryResult.message}
          <p class="fr-error-text">{tryMessage(tryResult)}</p>
        {:else}
          <p id="dataset-check-try-verdict" class="font-bold mb-3!">
            {tryResult.published
              ? m['admin.publishing.datasetCheck.try.published']()
              : m['admin.publishing.datasetCheck.try.excluded']()}
            <span class="text-sm text-grey font-normal">
              · {m['admin.promptChecks.bench.latency']({ count: tryResult.latency_ms })}
            </span>
          </p>
          <ul class="m-0! p-0! gap-2 mb-4! flex list-none flex-col">
            {#each tryCriteria as criterion (criterion.key)}
              {@const score = tryResult.scores[criterion.key] ?? 0}
              <li id="dataset-check-try-row-{criterion.key}" class="text-sm gap-2 flex">
                <span class="flex-1">{criterion.label}</span>
                <span class="font-bold tabular-nums">{formatScore(score)}</span>
                <span class="text-grey w-[9rem] text-right">
                  {tryResult.excluded_by.includes(criterion.key)
                    ? m['admin.publishing.datasetCheck.try.reached']()
                    : m['admin.publishing.datasetCheck.try.notReached']()}
                  ({formatScore(criterion.threshold)})
                </span>
              </li>
            {/each}
          </ul>
          <p class="text-sm mb-1!">
            <strong>{m['admin.publishing.datasetCheck.try.categories']()}</strong>
            {tryResult.categories.join(', ')}
          </p>
          <p class="text-sm mb-3!">
            <strong>{m['admin.publishing.datasetCheck.try.languages']()}</strong>
            {tryResult.languages.join(', ') || m['admin.publishing.datasetCheck.try.none']()}
          </p>
          <details>
            <summary class="text-sm cursor-pointer">
              {m['admin.publishing.datasetCheck.try.allScores']()}
            </summary>
            <ul class="m-0! p-0! mt-2 text-xs sm:grid-cols-2 gap-x-6 grid list-none">
              {#each Object.entries(tryResult.scores) as [key, score] (key)}
                <li class="gap-2 flex justify-between">
                  <span class="min-w-0 truncate">{key}</span>
                  <span class="tabular-nums">{formatScore(score)}</span>
                </li>
              {/each}
            </ul>
          </details>
        {/if}
      </div>
    {/if}
  </section>
</div>

<style lang="postcss">
  /* Same tint as the FormInput fields of the form, as on the prompt check. */
  :global(#dataset-check-form textarea.fr-input) {
    --border-plain-grey: var(--blue-france-main-525);
    --background-contrast-grey: var(--blue-ecume-975-75);
  }
</style>
