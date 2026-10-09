<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import type { AgentTraceToolCall } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import {
    isWebSearch,
    linkify,
    toolRequest,
    toolResultText,
    webSources,
    type ActivityStep,
    type WebSource
  } from './toolActivity'

  export type AgentActivityProps = {
    id: string
    /** Consecutive reasoning and tool calls, with no answer text between them. */
    steps: ActivityStep[]
    /** True while the model is still on these steps. */
    active: boolean
  }

  let { id, steps, active }: AgentActivityProps = $props()

  type Row = {
    kind: string
    label: string
    icon: string
    steps: ActivityStep[]
    sources: WebSource[]
  }

  function toolName(call: AgentTraceToolCall) {
    return call.label || call.name
  }

  function toolIcon(call: AgentTraceToolCall) {
    return isWebSearch(call) ? 'i-ri-global-line' : 'i-ri-tools-line'
  }

  // One row per step, in the order the model took them. Calls to the same
  // tool in a row share one, so three searches in a row read as one search.
  const rows = $derived.by(() => {
    const rows: Row[] = []
    for (const step of steps) {
      const kind =
        step.type === 'tool' ? `tool:${step.call.tool || toolName(step.call)}` : 'reasoning'
      const last = rows.at(-1)
      if (last?.kind === kind) {
        last.steps.push(step)
        continue
      }
      rows.push({
        kind,
        label: step.type === 'tool' ? toolName(step.call) : m['chatbot.activity.reasoning'](),
        icon: step.type === 'tool' ? toolIcon(step.call) : 'i-ri-brain-2-line',
        steps: [step],
        sources: []
      })
    }
    for (const row of rows) {
      const results = row.steps.flatMap((step) =>
        step.type === 'tool' && step.result ? [step.result] : []
      )
      row.sources = webSources(results)
      const calls = row.steps.filter((step) => step.type === 'tool')
      if (calls.length && calls.every((step) => step.result?.status === 'error')) {
        row.icon = 'i-ri-error-warning-line'
      }
    }
    return rows
  })

  let openIndex = $state<number | null>(null)

  // While it works, one line says what the model is doing now, as ChatGPT
  // does, with the tool's name in it.
  const live = $derived.by(() => {
    const current = steps.at(-1)
    if (current?.type === 'tool' && !current.result) {
      return isWebSearch(current.call)
        ? { verb: m['chatbot.activity.searching']() }
        : { verb: m['chatbot.activity.calling'](), name: toolName(current.call) }
    }
    return {
      verb:
        current?.type === 'tool'
          ? m['chatbot.activity.reading']()
          : m['chatbot.activity.thinking']()
    }
  })

  function favicons(sources: WebSource[]) {
    return [
      ...new Set(sources.flatMap((source) => (source.favicon ? [source.favicon] : [])))
    ].slice(0, 3)
  }

  function hideBrokenImage(event: Event) {
    const image = event.currentTarget
    if (image instanceof HTMLImageElement) image.hidden = true
  }
</script>

{#if active}
  <p class="agent-activity__live my-3! text-sm" aria-live="polite">
    {live.verb}
    {#if live.name}<strong>{live.name}</strong>{/if}
  </p>
{:else}
  <ol class="agent-activity__steps my-3! p-0! flex list-none! flex-col items-start">
    {#each rows as row, rowIndex (rowIndex)}
      {@const icons = favicons(row.sources)}
      <li class="p-0! flex w-full flex-col items-start">
        <button
          type="button"
          class="agent-activity__chip gap-1.5 px-2.5 text-sm font-medium flex items-center rounded-full"
          aria-expanded={openIndex === rowIndex}
          aria-controls="{id}-panel-{rowIndex}"
          onclick={() => (openIndex = openIndex === rowIndex ? null : rowIndex)}
        >
          <Icon icon={row.icon} size="xs" class="agent-activity__icon" />
          {row.label}
          {#if row.sources.length > 0}
            {#if icons.length > 0}
              <span class="agent-activity__favicons flex" aria-hidden="true">
                {#each icons as favicon (favicon)}
                  <img src={favicon} alt="" loading="lazy" onerror={hideBrokenImage} />
                {/each}
              </span>
            {/if}
            <span aria-hidden="true">{row.sources.length}</span>
            <span class="fr-sr-only">
              {row.sources.length === 1
                ? m['chatbot.activity.source']()
                : m['chatbot.activity.sources']({ count: row.sources.length })}
            </span>
          {/if}
        </button>

        <div
          id="{id}-panel-{rowIndex}"
          class="agent-activity__panel mt-1.5 gap-3 px-3 py-2.5 text-sm rounded-lg flex w-full flex-col"
          hidden={openIndex !== rowIndex}
        >
          {#each row.steps as step, index (index)}
            {#if step.type === 'reasoning'}
              <p class="mb-0! whitespace-pre-line text-[--text-mention-grey]">{step.content}</p>
            {:else}
              {@const request = toolRequest(step.call)}
              {@const sources = step.result ? webSources([step.result]) : []}
              {@const text = step.result && !sources.length ? toolResultText(step.result) : null}
              <div>
                {#if request || !isWebSearch(step.call)}
                  <p class="gap-x-2 mb-1! flex flex-wrap items-baseline text-[--text-mention-grey]">
                    {#if request}<span class="break-words">«&nbsp;{request}&nbsp;»</span>{/if}
                    {#if !isWebSearch(step.call)}<code class="text-xs">{step.call.name}</code>{/if}
                  </p>
                {/if}
                {#if sources.length > 0}
                  <ul class="m-0! gap-1 p-0! flex list-none! flex-col">
                    {#each sources as source (source.url)}
                      <li class="gap-2 p-0! flex items-start">
                        {#if source.favicon}
                          <img
                            src={source.favicon}
                            alt=""
                            aria-hidden="true"
                            loading="lazy"
                            onerror={hideBrokenImage}
                            class="mt-1 h-[14px] w-[14px] shrink-0"
                          />
                        {/if}
                        <Link
                          href={source.url}
                          text={source.name}
                          class="text-sm!"
                          style="--underline-img: none"
                        />
                      </li>
                    {/each}
                  </ul>
                {:else if text}
                  <!-- Raw tool output can run to pages. A short box that scrolls
                   keeps it from pushing the answer out of view. -->
                  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
                  <p
                    class="agent-activity__output mb-0! text-xs break-words whitespace-pre-line"
                    tabindex="0"
                    aria-label={m['chatbot.activity.output']({ tool: toolName(step.call) })}
                  >
                    {#each linkify(text) as segment, segmentIndex (segmentIndex)}
                      {#if segment.url}
                        <Link
                          href={segment.url}
                          text={segment.text}
                          class="text-xs!"
                          style="--underline-img: none"
                        />
                      {:else}
                        {segment.text}
                      {/if}
                    {/each}
                  </p>
                {:else}
                  <p class="mb-0! text-xs text-[--text-mention-grey]">
                    {step.result?.status === 'error'
                      ? m['chatbot.activity.failed']()
                      : m['chatbot.tools.noResult']()}
                  </p>
                {/if}
              </div>
            {/if}
          {/each}
        </div>
      </li>
    {/each}
  </ol>
{/if}

<style>
  /* A light band crossing the grey text while the model works, as ChatGPT
     does. It replaces a spinner, so the line keeps its height. */
  .agent-activity__live {
    background: linear-gradient(
        90deg,
        var(--text-mention-grey) 0%,
        var(--text-mention-grey) 40%,
        var(--text-default-grey) 50%,
        var(--text-mention-grey) 60%,
        var(--text-mention-grey) 100%
      )
      0 0 / 250% 100%;
    background-clip: text;
    -webkit-background-clip: text;
    color: transparent;
    animation: agent-activity-shimmer 2s linear infinite;
  }

  .agent-activity__live strong {
    color: transparent;
    font-weight: 600;
  }

  @keyframes agent-activity-shimmer {
    from {
      background-position: 100% 0;
    }
    to {
      background-position: 0% 0;
    }
  }

  /* A short line joins each step to the next, so they read as a sequence. */
  .agent-activity__steps > li + li::before {
    content: '';
    display: block;
    width: 1px;
    height: 0.5rem;
    margin-inline-start: 1rem;
    background: var(--border-default-grey);
  }

  .agent-activity__chip {
    --chip-background: var(--background-alt-grey);
    height: 1.75rem;
    color: var(--text-default-grey);
    background: var(--chip-background);
  }

  .agent-activity__chip:hover {
    --chip-background: var(--background-alt-grey-hover);
  }

  .agent-activity__chip[aria-expanded='true'] {
    --chip-background: var(--background-action-low-blue-france);
    box-shadow: inset 0 0 0 1px var(--border-action-high-blue-france);
  }

  .agent-activity__chip :global(.agent-activity__icon) {
    color: var(--text-action-high-blue-france);
  }

  .agent-activity__chip :global(.i-ri-error-warning-line) {
    color: var(--text-default-error);
  }

  .agent-activity__favicons img {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--background-default-grey);
    box-shadow: 0 0 0 2px var(--chip-background);
  }

  .agent-activity__favicons img + img {
    margin-inline-start: -4px;
  }

  .agent-activity__panel {
    background: var(--background-alt-grey);
  }

  .agent-activity__panel > :global(* + *) {
    padding-top: 0.75rem;
    border-top: 1px solid var(--border-default-grey);
  }

  .agent-activity__output {
    max-height: 10rem;
    overflow-y: auto;
    color: var(--text-mention-grey);
  }

  @media (prefers-reduced-motion: reduce) {
    .agent-activity__live {
      animation: none;
      background: none;
      color: var(--text-mention-grey);
    }

    .agent-activity__live strong {
      color: var(--text-default-grey);
    }
  }
</style>
