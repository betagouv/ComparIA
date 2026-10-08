<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation'
  import { resolve } from '$app/paths'
  import ToolCard from '$components/ToolCard.svelte'
  import {
    Alert,
    Badge,
    Button,
    Checkbox,
    Icon,
    Input,
    Segmented,
    Textarea,
    Toggle
  } from '$components/dsfr'
  import { api, ValidationError } from '$lib/fastapi-client'
  import type { ToolAdmin, ToolUpsert } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { tick } from 'svelte'
  import type { PageProps } from './$types'
  import { MCP_PRESETS, toKey, uniqueKey, type ToolPreset } from './presets'

  type ToolTestResult = {
    ok: boolean
    error: keyof typeof testErrors | null
    functions: { name: string; description: string }[] | null
  }
  type Choice = { kind: 'mcp'; preset?: ToolPreset } | { kind: 'builtin' }
  type Scope = 'all' | 'only' | 'except'

  const WEB_SEARCH = 'web_search'
  const DOMAINS_EXAMPLE = 'service-public.fr\nlegifrance.gouv.fr'

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
    m['admin.tools.wizard.steps.choose'](),
    m['admin.tools.wizard.steps.connect'](),
    m['admin.tools.wizard.steps.limit'](),
    m['admin.tools.wizard.steps.present'](),
    m['admin.tools.wizard.steps.review']()
  ]

  let step = $state(0)
  let heading = $state<HTMLHeadingElement>()

  let choice = $state<Choice>()
  let url = $state('')
  let secret = $state('')
  let testing = $state(false)
  let testResult = $state<ToolTestResult>()
  let allowedFunctions = $state<string[]>([])
  let scope = $state<Scope>('all')
  let domains = $state('')
  let label = $state('')
  let description = $state('')
  let enabled = $state(true)
  let saving = $state(false)
  let saveErrors = $state<string[]>([])

  const existing = $derived(data.tools as ToolAdmin[])
  const takenKeys = $derived(existing.map((tool) => tool.key))
  const takenUrls = $derived(existing.map((tool) => tool.url).filter(Boolean))
  const webSearchRow = $derived(existing.find((tool) => tool.key === WEB_SEARCH))

  const isMcp = $derived(choice?.kind === 'mcp')
  const key = $derived(isMcp ? uniqueKey(toKey(label), takenKeys) : WEB_SEARCH)
  const functions = $derived(testResult?.functions ?? [])
  const domainList = $derived(
    domains
      .split(/[\s,]+/)
      .map((domain) => domain.trim())
      .filter(Boolean)
  )

  const canContinue = $derived(
    [
      !!choice,
      !!testResult?.ok,
      isMcp ? allowedFunctions.length > 0 : scope === 'all' || domainList.length > 0,
      label.trim().length > 0,
      true
    ][step]
  )

  async function goTo(index: number) {
    step = index
    saveErrors = []
    await tick()
    heading?.focus()
  }

  function choose(next: Choice) {
    choice = next
    testResult = undefined
    allowedFunctions = []
    secret = ''
    if (next.kind === 'mcp') {
      url = next.preset?.url ?? ''
      label = next.preset?.label ?? ''
      description = next.preset?.description ?? ''
    } else {
      url = ''
      label = m['admin.tools.wizard.choose.webSearch']()
      description = m['admin.tools.wizard.choose.webSearchDescription']()
    }
    goTo(1)
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
        body: JSON.stringify({ kind: choice!.kind, key, url: url || null, secret: secret || null })
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
    const allTicked = allowedFunctions.length === functions.length
    const body: ToolUpsert = {
      key,
      label: label.trim(),
      description: description.trim() || null,
      kind: choice!.kind,
      url: isMcp ? url.trim() : null,
      // All ticked is stored as no list, so functions the server adds later
      // are offered too, as the step said.
      allowed_functions: isMcp && !allTicked ? allowedFunctions : null,
      allowed_domains: !isMcp && scope === 'only' ? domainList : null,
      blocked_domains: !isMcp && scope === 'except' ? domainList : null,
      enabled,
      secret: secret.trim() || null
    }
    try {
      const created = await api.request<ToolAdmin>('/admin/tools/tool', {
        method: 'post',
        body: JSON.stringify(body)
      })
      useToast(m['admin.tools.wizard.review.created'](), 5000, 'success')
      await invalidateAll()
      await goto(resolve(`/admin/outils/${created.id}`))
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
      {m['admin.tools.wizard.choose.title']()}
    </h2>
    <p class="mb-6! text-[--text-mention-grey]">{m['admin.tools.wizard.choose.hint']()}</p>

    <h3 class="fr-text--md font-bold mb-3!">{m['admin.tools.wizard.choose.presets']()}</h3>
    <ul class="m-0 mb-8 gap-3 p-0 md:grid-cols-2 grid list-none">
      {#each MCP_PRESETS as preset (preset.key)}
        {@const added = takenUrls.includes(preset.url)}
        <li class="p-0">
          <button
            type="button"
            class="choice-card gap-1 rounded-xl px-4 py-3 flex h-full w-full flex-col text-left"
            disabled={added}
            onclick={() => choose({ kind: 'mcp', preset })}
          >
            <span class="gap-2 flex w-full items-center justify-between">
              <span class="font-bold">{preset.label}</span>
              {#if added}
                <Badge size="sm" text={m['admin.tools.wizard.choose.added']()} />
              {:else}
                <span class="fr-text--xs mb-0! text-[--text-mention-grey]">{preset.source}</span>
              {/if}
            </span>
            <span class="fr-text--sm mb-0! text-[--text-mention-grey]">{preset.description}</span>
          </button>
        </li>
      {/each}
    </ul>

    <h3 class="fr-text--md font-bold mb-3!">{m['admin.tools.wizard.choose.custom']()}</h3>
    <ul class="m-0 gap-3 p-0 md:grid-cols-2 grid list-none">
      <li class="p-0">
        <button
          type="button"
          class="choice-card gap-3 rounded-xl px-4 py-3 flex h-full w-full items-start text-left"
          onclick={() => choose({ kind: 'mcp' })}
        >
          <Icon icon="i-ri-plug-line" class="mt-1 text-primary" />
          <span>
            <span class="font-bold block">{m['admin.tools.wizard.choose.other']()}</span>
            <span class="fr-text--sm mb-0! block text-[--text-mention-grey]">
              {m['admin.tools.wizard.choose.otherHint']()}
            </span>
          </span>
        </button>
      </li>
      <li class="p-0">
        <button
          type="button"
          class="choice-card gap-3 rounded-xl px-4 py-3 flex h-full w-full items-start text-left"
          disabled={!!webSearchRow}
          onclick={() => choose({ kind: 'builtin' })}
        >
          <Icon icon="i-ri-search-line" class="mt-1 text-primary" />
          <span>
            <span class="font-bold block">{m['admin.tools.wizard.choose.webSearch']()}</span>
            <span class="fr-text--sm mb-0! block text-[--text-mention-grey]">
              {webSearchRow
                ? m['admin.tools.wizard.choose.webSearchExists']()
                : m['admin.tools.wizard.choose.webSearchHint']()}
            </span>
          </span>
        </button>
      </li>
    </ul>
  {:else if step === 1}
    <h2 bind:this={heading} tabindex="-1" class="fr-h4 mb-2!">
      {isMcp
        ? m['admin.tools.wizard.connect.title']()
        : m['admin.tools.wizard.connect.titleWebSearch']()}
    </h2>
    <p class="mb-6! text-[--text-mention-grey]">{m['admin.tools.wizard.connect.hint']()}</p>

    {#if isMcp}
      <Input
        id="wizard-url"
        type="url"
        label={m['admin.tools.wizard.connect.url']()}
        help={m['admin.tools.wizard.connect.urlHint']()}
        placeholder="https://exemple.fr/mcp"
        bind:value={url}
        oninput={changed}
      />
    {/if}
    <Input
      id="wizard-secret"
      type="password"
      autocomplete="off"
      label={isMcp
        ? m['admin.tools.wizard.connect.secretMcp']()
        : m['admin.tools.wizard.connect.secretWebSearch']()}
      help={isMcp
        ? m['admin.tools.wizard.connect.secretMcpHint']()
        : m['admin.tools.wizard.connect.secretWebSearchHint']()}
      bind:value={secret}
      oninput={changed}
    />

    <Button
      id="wizard-test"
      icon="flashlight-line"
      variant="secondary"
      text={testing ? m['admin.tools.testing']() : m['admin.tools.wizard.connect.test']()}
      disabled={testing || (isMcp && !url.trim())}
      onclick={runTest}
    />
    <div aria-live="polite" class="mt-4">
      {#if testResult?.ok}
        <Alert
          small
          variant="success"
          title={testResult.functions
            ? m['admin.tools.testOkFunctions']({ count: testResult.functions.length })
            : m['admin.tools.testOk']()}
        />
      {:else if testResult}
        <Alert variant="error" title={m['admin.tools.testFailed']()}>
          <p>{testResult.error ? testErrors[testResult.error]() : ''}</p>
        </Alert>
      {/if}
    </div>
  {:else if step === 2}
    {#if isMcp}
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
    {:else}
      <h2 bind:this={heading} tabindex="-1" class="fr-h4 mb-2!">
        {m['admin.tools.wizard.limit.titleWebSearch']()}
      </h2>
      <p class="mb-6! text-[--text-mention-grey]">
        {m['admin.tools.wizard.limit.hintWebSearch']()}
      </p>
      <Segmented
        id="wizard-scope"
        legend={m['admin.tools.wizard.limit.scope']()}
        bind:value={scope}
        options={[
          { value: 'all', label: m['admin.tools.wizard.limit.scopeAll']() },
          { value: 'only', label: m['admin.tools.wizard.limit.scopeOnly']() },
          { value: 'except', label: m['admin.tools.wizard.limit.scopeExcept']() }
        ]}
        class="mb-6!"
      />
      {#if scope !== 'all'}
        <Textarea
          id="wizard-domains"
          rows={4}
          label={m['admin.tools.wizard.limit.domains']()}
          help={m['admin.tools.wizard.limit.domainsHint']()}
          placeholder={DOMAINS_EXAMPLE}
          bind:value={domains}
        />
      {/if}
    {/if}
  {:else if step === 3}
    <h2 bind:this={heading} tabindex="-1" class="fr-h4 mb-2!">
      {m['admin.tools.wizard.present.title']()}
    </h2>
    <p class="mb-6! text-[--text-mention-grey]">{m['admin.tools.wizard.present.hint']()}</p>

    <div class="gap-8 md:grid-cols-2 grid">
      <div>
        <Input
          id="wizard-label"
          label={m['admin.tools.wizard.present.label']()}
          help={isMcp ? m['admin.tools.wizard.present.key']({ key }) : undefined}
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
      {@render row(
        m['admin.tools.wizard.review.kind'](),
        isMcp ? m['admin.tools.wizard.review.mcp']() : m['admin.tools.wizard.choose.webSearch'](),
        0
      )}
      {#if isMcp}
        {@render row(m['admin.tools.wizard.connect.url'](), url, 1)}
      {/if}
      {@render row(
        m['admin.tools.wizard.review.secret'](),
        secret.trim() ? m['admin.tools.secretSet']() : m['admin.tools.secretUnset'](),
        1
      )}
      {#if isMcp}
        {@render row(
          m['admin.tools.wizard.review.functions'](),
          allowedFunctions.length === functions.length
            ? m['admin.tools.wizard.review.allFunctions']({ count: functions.length })
            : `${m['admin.tools.wizard.limit.count']({
                count: allowedFunctions.length,
                total: functions.length
              })} : ${allowedFunctions.join(', ')}`,
          2
        )}
      {:else}
        {@render row(
          m['admin.tools.wizard.limit.scope'](),
          scope === 'all'
            ? m['admin.tools.wizard.limit.scopeAll']()
            : `${
                scope === 'only'
                  ? m['admin.tools.wizard.limit.scopeOnly']()
                  : m['admin.tools.wizard.limit.scopeExcept']()
              } : ${domainList.join(', ')}`,
          2
        )}
      {/if}
      {@render row(m['admin.tools.wizard.present.label'](), label.trim(), 3)}
      {@render row(
        m['admin.tools.wizard.present.description'](),
        description.trim() || m['admin.tools.wizard.review.noDescription'](),
        3
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

  {#if step > 0}
    <div class="mt-8 gap-4 pt-6 flex justify-between border-t border-[--border-default-grey]">
      <Button variant="secondary" text={m['words.back']()} onclick={() => goTo(step - 1)} />
      {#if step < steps.length - 1}
        <Button
          id="wizard-next"
          text={m['admin.tools.wizard.next']()}
          disabled={!canContinue}
          title={!canContinue && step === 1
            ? m['admin.tools.wizard.connect.mustTest']()
            : undefined}
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
    {#if step === 1 && !canContinue}
      <p class="fr-text--sm mt-2! text-end text-[--text-mention-grey]">
        {m['admin.tools.wizard.connect.mustTest']()}
      </p>
    {/if}
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

  .choice-card {
    background-color: var(--background-default-grey);
    border: 1px solid var(--border-default-grey);
    transition: border-color 120ms ease-out;
  }

  .choice-card:hover:not(:disabled) {
    border-color: var(--blue-france-main-525);
  }

  .choice-card:disabled {
    cursor: default;
    opacity: 0.6;
  }

  h2:focus {
    outline: none;
  }
</style>
