<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation'
  import { resolve } from '$app/paths'
  import ToolCard from '$components/ToolCard.svelte'
  import { Alert, Button, Checkbox, Input, Textarea, Toggle } from '$components/dsfr'
  import Link from '$components/dsfr/Link.svelte'
  import { api, ValidationError } from '$lib/fastapi-client'
  import type { ToolAdmin, ToolUpsert } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { tick } from 'svelte'
  import type { PageProps } from './$types'
  import { toKey, uniqueKey } from './keys'

  type ToolTestResult = {
    ok: boolean
    error: keyof typeof testErrors | null
    functions: { name: string; description: string }[] | null
  }

  const testErrors = {
    no_credential: m['admin.tools.errors.no_credential'],
    no_url: m['admin.tools.errors.no_url'],
    invalid_credential: m['admin.tools.errors.invalid_credential'],
    no_credit: m['admin.tools.errors.no_credit'],
    unreachable: m['admin.tools.errors.unreachable'],
    timeout: m['admin.tools.errors.timeout'],
    unknown_builtin: m['admin.tools.errors.unknown_builtin']
  }

  const { data }: PageProps = $props()

  const steps = [
    m['admin.tools.wizard.steps.connect'](),
    m['admin.tools.wizard.steps.limit'](),
    m['admin.tools.wizard.steps.present'](),
    m['admin.tools.wizard.steps.review']()
  ]

  let step = $state(0)
  let heading = $state<HTMLHeadingElement>()

  let url = $state('')
  let secret = $state('')
  let testing = $state(false)
  let testResult = $state<ToolTestResult>()
  let allowedFunctions = $state<string[]>([])
  let label = $state('')
  let description = $state('')
  let enabled = $state(true)
  let saving = $state(false)
  let saveErrors = $state<string[]>([])

  const takenKeys = $derived((data.tools as ToolAdmin[]).map((tool) => tool.key))
  const key = $derived(uniqueKey(toKey(label), takenKeys))
  const functions = $derived(testResult?.functions ?? [])

  const canContinue = $derived(
    [!!testResult?.ok, allowedFunctions.length > 0, label.trim().length > 0, true][step]
  )

  async function goTo(index: number) {
    step = index
    saveErrors = []
    await tick()
    heading?.focus()
  }

  // A test only stands for what it was run with.
  function changed() {
    testResult = undefined
  }

  async function runTest() {
    testing = true
    testResult = undefined
    try {
      testResult = await api.request<ToolTestResult>('/admin/tools/test', {
        method: 'post',
        body: JSON.stringify({ kind: 'mcp', url: url.trim(), secret: secret || null })
      })
      // Everything the server offers starts ticked; unticking is the choice.
      allowedFunctions = testResult.functions?.map((f) => f.name) ?? []
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      testing = false
    }
  }

  // Servers write their descriptions for models, at length. The first
  // sentence is enough to choose by.
  function firstSentence(text: string) {
    return text.split(/(?<=\.)\s/)[0]
  }

  function toggleFunction(name: string, checked: boolean) {
    const others = allowedFunctions.filter((n) => n !== name)
    allowedFunctions = checked ? [...others, name] : others
  }

  async function create() {
    saving = true
    saveErrors = []
    const body: ToolUpsert = {
      key,
      label: label.trim(),
      description: description.trim() || null,
      kind: 'mcp',
      url: url.trim(),
      // All ticked is stored as no list, so functions the server adds later
      // are offered too, as the step said.
      allowed_functions: allowedFunctions.length === functions.length ? null : allowedFunctions,
      enabled,
      secret: secret.trim() || null
    }
    try {
      await api.request<ToolAdmin>('/admin/tools/tool', {
        method: 'post',
        body: JSON.stringify(body)
      })
      useToast(m['admin.tools.wizard.review.created']({ label: body.label }), 5000, 'success')
      await invalidateAll()
      await goto(resolve('/admin/outils'))
    } catch (error) {
      saveErrors =
        error instanceof ValidationError && error.errors
          ? error.errors.map((e) => e.msg)
          : [(error as Error).message]
    } finally {
      saving = false
    }
  }
</script>

<div class="max-w-[800px]">
  <nav aria-label={m['admin.tools.wizard.progress']()} class="mb-8">
    <p class="fr-text--sm mb-3! text-[--text-mention-grey]">
      {m['admin.tools.wizard.stepState']({ current: step + 1, total: steps.length })}
    </p>
    <!-- DSFR numbers ordered lists through ::marker; the bars stand in. -->
    <ol class="m-0 gap-2 p-0 flex list-none" style="--ol-content: none">
      {#each steps as name, index (name)}
        <li class="min-w-0 p-0 flex-1">
          <button
            type="button"
            class={[
              'wizard-step w-full text-left',
              { done: index < step, current: index === step }
            ]}
            aria-current={index === step ? 'step' : undefined}
            disabled={index >= step}
            onclick={() => goTo(index)}
          >
            <span class="wizard-step__bar mb-2 block"></span>
            <span class="fr-text--sm mb-0! block truncate">{name}</span>
          </button>
        </li>
      {/each}
    </ol>
  </nav>

  {#if step === 0}
    <h2 bind:this={heading} tabindex="-1" class="fr-h4 mb-2!">
      {m['admin.tools.wizard.connect.title']()}
    </h2>
    <p class="mb-6! text-[--text-mention-grey]">{m['admin.tools.wizard.connect.hint']()}</p>

    <Input
      id="wizard-url"
      type="url"
      label={m['admin.tools.wizard.connect.url']()}
      help={m['admin.tools.wizard.connect.urlHint']()}
      placeholder="https://exemple.fr/mcp"
      bind:value={url}
      oninput={changed}
    />
    <Input
      id="wizard-secret"
      type="password"
      autocomplete="off"
      label={m['admin.tools.wizard.connect.secret']()}
      help={m['admin.tools.wizard.connect.secretHint']()}
      bind:value={secret}
      oninput={changed}
    />

    <Button
      id="wizard-test"
      icon="flashlight-line"
      variant="secondary"
      text={testing ? m['admin.tools.testing']() : m['admin.tools.wizard.connect.test']()}
      disabled={testing || !url.trim()}
      onclick={runTest}
    />
    <div aria-live="polite" class="mt-4">
      {#if testResult?.ok}
        <Alert
          small
          variant="success"
          title={m['admin.tools.testOkFunctions']({ count: functions.length })}
        />
      {:else if testResult}
        <Alert variant="error" title={m['admin.tools.testFailed']()}>
          <p>{testResult.error ? testErrors[testResult.error]() : ''}</p>
        </Alert>
      {/if}
    </div>
  {:else if step === 1}
    <h2 bind:this={heading} tabindex="-1" class="fr-h4 mb-2!">
      {m['admin.tools.wizard.limit.title']()}
    </h2>
    <p class="mb-4! text-[--text-mention-grey]">{m['admin.tools.wizard.limit.hint']()}</p>
    <div class="mb-2 gap-2 flex">
      <Button
        size="sm"
        variant="tertiary-no-outline"
        text={m['admin.tools.wizard.limit.all']()}
        onclick={() => (allowedFunctions = functions.map((f) => f.name))}
      />
      <Button
        size="sm"
        variant="tertiary-no-outline"
        text={m['admin.tools.wizard.limit.none']()}
        onclick={() => (allowedFunctions = [])}
      />
    </div>
    <fieldset class="fr-fieldset" aria-labelledby="wizard-functions-legend">
      <legend id="wizard-functions-legend" class="fr-sr-only">
        {m['admin.tools.functionsLegend']()}
      </legend>
      {#each functions as fn (fn.name)}
        <div class="fr-fieldset__element">
          <Checkbox
            id="wizard-function-{fn.name}"
            label={fn.name}
            help={firstSentence(fn.description)}
            bind:checked={
              () => allowedFunctions.includes(fn.name),
              (checked) => toggleFunction(fn.name, checked)
            }
          />
        </div>
      {/each}
    </fieldset>
    <p class="fr-text--sm text-[--text-mention-grey]" aria-live="polite">
      {allowedFunctions.length === 0
        ? m['admin.tools.wizard.limit.needOne']()
        : m['admin.tools.wizard.limit.count']({
            count: allowedFunctions.length,
            total: functions.length
          })}
    </p>
  {:else if step === 2}
    <h2 bind:this={heading} tabindex="-1" class="fr-h4 mb-2!">
      {m['admin.tools.wizard.present.title']()}
    </h2>
    <p class="mb-6! text-[--text-mention-grey]">{m['admin.tools.wizard.present.hint']()}</p>

    <div class="gap-8 md:grid-cols-2 grid">
      <div>
        <Input
          id="wizard-label"
          label={m['admin.tools.wizard.present.label']()}
          help={m['admin.tools.wizard.present.key']({ key })}
          maxlength={60}
          required
          bind:value={label}
        />
        <Textarea
          id="wizard-description"
          rows={3}
          maxlength={160}
          label={m['admin.tools.wizard.present.description']()}
          help={m['admin.tools.wizard.present.descriptionHint']()}
          bind:value={description}
        />
      </div>
      <div>
        <p class="fr-text--sm font-bold mb-2!">{m['admin.tools.wizard.present.preview']()}</p>
        <div class="p-4 rounded-xl bg-[--background-alt-grey]">
          <ToolCard
            id="preview"
            label={label.trim() || m['admin.tools.wizard.present.label']()}
            description={description.trim()}
            pressed
          />
        </div>
      </div>
    </div>
  {:else}
    <h2 bind:this={heading} tabindex="-1" class="fr-h4 mb-6!">
      {m['admin.tools.wizard.review.title']()}
    </h2>

    {#snippet row(name: string, value: string, back: number)}
      <div
        class="gap-4 py-3 flex items-start justify-between border-b border-[--border-default-grey]"
      >
        <div class="min-w-0">
          <dt class="fr-text--sm mb-0! ps-0! text-[--text-mention-grey]">{name}</dt>
          <dd class="m-0! ps-0! break-words">{value}</dd>
        </div>
        <Button
          size="sm"
          variant="tertiary-no-outline"
          text={m['admin.tools.wizard.review.edit']()}
          aria-label="{m['admin.tools.wizard.review.edit']()} : {name}"
          onclick={() => goTo(back)}
        />
      </div>
    {/snippet}

    <dl class="m-0 mb-6 ps-0!">
      {@render row(m['admin.tools.wizard.connect.url'](), url.trim(), 0)}
      {@render row(
        m['admin.tools.wizard.review.secret'](),
        secret.trim() ? m['admin.tools.secretSet']() : m['admin.tools.secretUnset'](),
        0
      )}
      {@render row(
        m['admin.tools.wizard.review.functions'](),
        allowedFunctions.length === functions.length
          ? m['admin.tools.wizard.review.allFunctions']({ count: functions.length })
          : `${m['admin.tools.wizard.limit.count']({
              count: allowedFunctions.length,
              total: functions.length
            })} : ${allowedFunctions.join(', ')}`,
        1
      )}
      {@render row(m['admin.tools.wizard.present.label'](), label.trim(), 2)}
      {@render row(
        m['admin.tools.wizard.present.description'](),
        description.trim() || m['admin.tools.wizard.review.noDescription'](),
        2
      )}
    </dl>

    <Toggle
      id="wizard-enabled"
      label={m['admin.tools.wizard.review.enable']()}
      help={m['admin.tools.wizard.review.enableHint']()}
      bind:value={enabled}
    />

    {#if saveErrors.length}
      <Alert variant="error" title={m['admin.tools.wizard.review.failed']()} class="mt-4">
        {#each saveErrors as error, index (index)}
          <p>{error}</p>
        {/each}
      </Alert>
    {/if}
  {/if}

  <div class="mt-8 gap-4 pt-6 flex justify-between border-t border-[--border-default-grey]">
    {#if step === 0}
      <Link button variant="secondary" text={m['words.cancel']()} href={resolve('/admin/outils')} />
    {:else}
      <Button variant="secondary" text={m['words.back']()} onclick={() => goTo(step - 1)} />
    {/if}
    {#if step < steps.length - 1}
      <Button
        id="wizard-next"
        text={m['admin.tools.wizard.next']()}
        disabled={!canContinue}
        onclick={() => goTo(step + 1)}
      />
    {:else}
      <Button
        id="wizard-create"
        icon="check-line"
        text={saving
          ? m['admin.tools.wizard.review.creating']()
          : m['admin.tools.wizard.review.create']()}
        disabled={saving}
        onclick={create}
      />
    {/if}
  </div>
  {#if step === 0 && !canContinue}
    <p class="fr-text--sm mt-2! text-end text-[--text-mention-grey]">
      {m['admin.tools.wizard.connect.mustTest']()}
    </p>
  {/if}
</div>

<style>
  .wizard-step {
    color: var(--text-mention-grey);
  }

  .wizard-step:disabled {
    cursor: default;
  }

  .wizard-step__bar {
    height: 6px;
    border-radius: 3px;
    background-color: var(--background-contrast-grey);
  }

  .wizard-step.done,
  .wizard-step.current {
    color: var(--text-default-grey);
  }

  .wizard-step.current {
    font-weight: 700;
  }

  .wizard-step.done .wizard-step__bar,
  .wizard-step.current .wizard-step__bar {
    background-color: var(--blue-france-main-525);
  }

  .wizard-step.done:hover {
    color: var(--blue-france-main-525);
  }

  h2:focus {
    outline: none;
  }
</style>
