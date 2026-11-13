<script lang="ts">
  import { Badge, Button } from '$components/dsfr'
  import { api, ValidationError } from '$lib/fastapi-client'
  import type { PreviewLLM, SelectionModePreview, SelectionModeRules } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import { errorText, requestErrorText } from '../errors'
  import { blockedByTools, ruleSummary, warningText } from '../summary'

  let {
    rules,
    toolLabel,
    preview = $bindable()
  }: {
    rules: SelectionModeRules
    /** A tool's name from its key, for the one-line rule. */
    toolLabel?: (key: string) => string
    preview?: SelectionModePreview
  } = $props()

  const DEBOUNCE_MS = 400

  let loading = $state(false)
  let error = $state<string>()
  let draws = $state<[PreviewLLM, PreviewLLM][]>()
  let drawing = $state(false)
  // An answer to an older version of the rules must not replace a newer one.
  let seq = 0

  const body = $derived(JSON.stringify(rules))
  const split = $derived(!!rules.pool_b)

  async function fetchPreview(payload: string) {
    const mine = ++seq
    loading = true
    try {
      const result = await api.request<SelectionModePreview>('/admin/selection-modes/preview', {
        method: 'POST',
        body: payload
      })
      if (mine !== seq) return
      preview = result
      error = undefined
      return result
    } catch (failure) {
      if (mine !== seq) return
      error =
        failure instanceof ValidationError && failure.errors
          ? failure.errors.map((e) => errorText(e)).join(' ')
          : requestErrorText(failure)
    } finally {
      if (mine === seq) loading = false
    }
  }

  $effect(() => {
    const payload = body
    // Examples drawn under other rules would say something false.
    draws = undefined
    const timer = setTimeout(() => fetchPreview(payload), DEBOUNCE_MS)
    return () => clearTimeout(timer)
  })

  async function drawExamples() {
    drawing = true
    try {
      const result = await fetchPreview(body)
      if (result) draws = result.sample_draws as [PreviewLLM, PreviewLLM][]
    } finally {
      drawing = false
    }
  }

  function count(size: number) {
    return size === 1
      ? m['admin.selectionModes.preview.oneModel']()
      : m['admin.selectionModes.preview.models']({ count: size })
  }
</script>

{#snippet name(model: PreviewLLM)}
  {model.name}
  {#if !model.arena_tools}
    <Badge
      size="xs"
      noTooltip
      class="ms-1"
      text={m['admin.selectionModes.preview.ownTools']()}
      title={m['admin.selectionModes.preview.ownToolsHelp']()}
    />
  {/if}
{/snippet}

{#snippet pool(title: string, models: PreviewLLM[] | undefined, listId: string)}
  <div class="mb-4">
    <h3 class="fr-text--md font-bold mb-1!" id="{listId}-title">
      {title}
      {#if models}
        <span class="font-normal text-[--text-mention-grey]">· {count(models.length)}</span>
      {/if}
    </h3>
    <!-- Focusable so the list scrolls from the keyboard. -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div
      class="pool-list rounded-md px-3 py-2 overflow-y-auto border border-[--border-default-grey]"
      tabindex="0"
      role="region"
      aria-labelledby="{listId}-title"
    >
      {#if !models}
        <!-- Same height as the list to come, so nothing moves when it lands. -->
      {:else if models.length}
        <ul class="m-0! p-0! list-none">
          {#each models as model (model.id)}
            <li class="fr-text--sm mb-0! py-0.5 gap-2 flex justify-between">
              <span class="min-w-0 break-words">{@render name(model)}</span>
              <span class="shrink-0 text-[--text-mention-grey]">{model.lab}</span>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="fr-text--sm mb-0! text-[--text-default-error]">
          {m['admin.selectionModes.preview.noModel']()}
        </p>
      {/if}
    </div>
  </div>
{/snippet}

<section class="p-4 md:p-5 cg-border bg-white" aria-labelledby="mode-preview-title">
  <div class="gap-2 flex items-baseline justify-between">
    <h2 id="mode-preview-title" class="fr-h6 mb-1!">{m['admin.selectionModes.preview.title']()}</h2>
    <span class="fr-text--xs mb-0! text-[--text-mention-grey]" aria-hidden="true">
      {loading ? m['admin.selectionModes.preview.updating']() : ''}
    </span>
  </div>
  <p class="fr-text--sm mb-4! text-[--text-mention-grey]">
    {m['admin.selectionModes.preview.intro']()}
  </p>

  <div aria-live="polite" class={['transition-opacity', { 'opacity-60': loading }]}>
    {#if error}
      <div class="status status--error">
        <p class="fr-text--sm font-bold mb-1!">{m['admin.selectionModes.preview.invalid']()}</p>
        <p class="fr-text--sm mb-0!">{error}</p>
      </div>
    {:else if preview}
      {@const viability = preview.viability}
      {@const toolsBlock = blockedByTools(rules, viability)}
      <div class={['status', viability.viable ? 'status--ok' : 'status--error']}>
        <p class="fr-text--sm font-bold mb-0!">
          {#if !viability.viable}
            {m['admin.selectionModes.preview.notViable']()}
          {:else if viability.pairs === 1}
            {m['admin.selectionModes.preview.onePair']()}
          {:else}
            {m['admin.selectionModes.preview.pairs']({ count: viability.pairs })}
          {/if}
        </p>
        <p class="fr-text--sm mt-1! mb-0!">{ruleSummary(rules, viability, toolLabel)}</p>
        {#if viability.warnings?.length}
          <ul class="fr-text--sm mt-2! mb-0! ps-4!">
            {#each viability.warnings as warning (warning)}
              <li>{warningText(warning, split, toolsBlock)}</li>
            {/each}
          </ul>
        {/if}
      </div>
    {:else}
      <div class="status">
        <p class="fr-text--sm mb-0!">{m['admin.selectionModes.preview.loading']()}</p>
      </div>
    {/if}
  </div>

  <div class={['mt-4', { 'opacity-60': loading }]}>
    {#if split}
      {@render pool(
        m['generated.selection_mode_upsert.pool_a.label'](),
        preview?.pool_a,
        'preview-pool-a'
      )}
      {@render pool(
        m['generated.selection_mode_upsert.pool_b.label'](),
        preview?.pool_b,
        'preview-pool-b'
      )}
    {:else}
      {@render pool(m['admin.selectionModes.pool.title'](), preview?.pool_a, 'preview-pool-a')}
    {/if}
  </div>

  <div class="mt-2 pt-4 border-t border-[--border-default-grey]">
    <Button
      variant="secondary"
      size="sm"
      icon="shuffle"
      text={drawing
        ? m['admin.selectionModes.preview.drawing']()
        : m['admin.selectionModes.preview.draw']()}
      disabled={drawing || !!error || !preview?.viability.viable}
      onclick={drawExamples}
    />
    <div aria-live="polite">
      {#if draws}
        {#if rules.visitor_picks}
          <p class="fr-hint-text mt-3!">{m['admin.selectionModes.preview.drawsNoPicks']()}</p>
        {/if}
        {#if split}
          <!-- Columns name the pool, not the side: the arena shuffles sides. -->
          <table class="draws mt-3! fr-text--sm">
            <thead>
              <tr>
                <th scope="col">{m['admin.selectionModes.preview.fromPoolA']()}</th>
                <th scope="col">{m['admin.selectionModes.preview.fromPoolB']()}</th>
              </tr>
            </thead>
            <tbody>
              {#each draws as [a, b], index (index)}
                <tr>
                  <td>{@render name(a)}</td>
                  <td>{@render name(b)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <ol class="mt-3! mb-0! ps-5! fr-text--sm">
            {#each draws as [a, b], index (index)}
              <li class="mb-1!">
                <span class="font-bold">{@render name(a)}</span>
                <span class="text-[--text-mention-grey]">
                  {m['admin.selectionModes.preview.versus']()}
                </span>
                <span class="font-bold">{@render name(b)}</span>
              </li>
            {/each}
          </ol>
        {/if}
      {/if}
    </div>
  </div>
</section>

<style>
  .pool-list {
    height: 9.5rem;
  }

  .draws th,
  .draws td {
    padding: 0.25rem 1rem 0.25rem 0;
    text-align: start;
    vertical-align: top;
  }

  .status {
    min-height: 3rem;
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid var(--border-default-grey);
    background-color: var(--background-alt-grey);
  }

  .status--ok {
    border-left-color: var(--border-plain-success);
    background-color: var(--background-contrast-success);
  }

  .status--error {
    border-left-color: var(--border-plain-error);
    background-color: var(--background-contrast-error);
  }
</style>
