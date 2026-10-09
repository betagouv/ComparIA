<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import type { AgentTraceToolCall } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import { SvelteSet } from 'svelte/reactivity'
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
    /** What the model asked, when the row holds a single call. */
    request: string | null
    /** How many calls the row holds, when there are several. */
    calls: string | null
  }

  const SOURCE_LIMIT = 5

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
        sources: [],
        request: null,
        calls: null
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
      if (calls.length === 1) row.request = toolRequest(calls[0].call)
      if (calls.length > 1) {
        row.calls = isWebSearch(calls[0].call)
          ? m['chatbot.activity.searches']({ count: calls.length })
          : m['chatbot.activity.calls']({ count: calls.length })
      }
    }
    return rows
  })

  let openIndex = $state<number | null>(null)
  // Long lists and answers the visitor chose to see in full.
  const expanded = new SvelteSet<string>()

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

  function site(url: string) {
    return new URL(url).hostname.replace(/^www\./, '')
  }

  function isLong(text: string) {
    return text.length > 400 || text.split('\n').length > 6
  }

  function toggle(key: string) {
    if (expanded.has(key)) expanded.delete(key)
    else expanded.add(key)
  }

  function hideBrokenImage(event: Event) {
    const image = event.currentTarget
    if (image instanceof HTMLImageElement) image.hidden = true
  }
</script>

{#snippet longText(key: string, text: string)}
  {@const full = expanded.has(key) || !isLong(text)}
  <p
    class={[
      'agent-activity__text mb-0! text-sm break-words whitespace-pre-line',
      { 'agent-activity__text--cut': !full }
    ]}
  >
    {#each linkify(text) as segment, segmentIndex (segmentIndex)}
      {#if segment.url}
        <Link href={segment.url} text={segment.text} class="text-sm!" />
      {:else}
        {segment.text}
      {/if}
    {/each}
  </p>
  {#if isLong(text)}
    <button
      type="button"
      class="agent-activity__more text-sm font-medium"
      onclick={() => toggle(key)}
    >
      {full ? m['chatbot.activity.collapse']() : m['chatbot.activity.showAll']()}
    </button>
  {/if}
{/snippet}

{#if active}
  <p class="agent-activity__live my-3! text-sm" aria-live="polite">
    {live.verb}
    {#if live.name}<strong>{live.name}</strong>{/if}
  </p>
{:else}
  <ol class="agent-activity__steps my-3! p-0! list-none!">
    {#each rows as row, rowIndex (rowIndex)}
      {@const open = openIndex === rowIndex}
      {@const icons = favicons(row.sources)}
      <!-- Each step is a line, its icon on the thread that joins them, with
           what the model asked beside the tool name. -->
      <li class="agent-activity__step p-0! relative">
        <span class="agent-activity__dot flex items-center justify-center rounded-full">
          <Icon icon={row.icon} size="xs" />
        </span>
        <div>
          <button
            type="button"
            class="agent-activity__head gap-2 text-sm flex w-full items-center text-left"
            aria-expanded={open}
            aria-controls="{id}-panel-{rowIndex}"
            onclick={() => (openIndex = open ? null : rowIndex)}
          >
            <span class="font-medium shrink-0">{row.label}</span>
            {#if row.request}
              <span class="agent-activity__request">«&nbsp;{row.request}&nbsp;»</span>
            {:else if row.calls}
              <span class="agent-activity__request">{row.calls}</span>
            {/if}
            {#if row.sources.length > 0}
              <span class="agent-activity__count gap-1 flex shrink-0 items-center">
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
              </span>
            {/if}
            <Icon
              icon="i-ri-arrow-right-s-line"
              size="sm"
              class="agent-activity__chevron ms-auto"
            />
          </button>

          <div id="{id}-panel-{rowIndex}" class="agent-activity__panel" hidden={!open}>
            <div class="agent-activity__panel-body gap-3 pt-1.5 pb-1 flex flex-col">
              {#each row.steps as step, index (index)}
                {@const key = `${rowIndex}-${index}`}
                {#if step.type === 'reasoning'}
                  <div>{@render longText(key, step.content)}</div>
                {:else}
                  {@const sources = step.result ? webSources([step.result]) : []}
                  {@const text =
                    step.result && !sources.length ? toolResultText(step.result) : null}
                  {@const request = row.request ? null : toolRequest(step.call)}
                  {@const shown = expanded.has(key) ? sources : sources.slice(0, SOURCE_LIMIT)}
                  <div>
                    {#if request}
                      <p class="mb-1! text-sm break-words text-[--text-mention-grey]">
                        «&nbsp;{request}&nbsp;»
                      </p>
                    {/if}
                    {#if sources.length > 0}
                      <ul class="m-0! p-0! flex list-none! flex-col">
                        {#each shown as source (source.url)}
                          <li class="p-0!">
                            <Link
                              href={source.url}
                              text={source.name}
                              hideExternalIcon
                              class="agent-activity__source gap-2 py-1! text-sm! flex! w-full items-center"
                            >
                              {#if source.favicon}
                                <img
                                  src={source.favicon}
                                  alt=""
                                  aria-hidden="true"
                                  loading="lazy"
                                  onerror={hideBrokenImage}
                                  class="h-[14px] w-[14px] shrink-0"
                                />
                              {/if}
                              <span class="agent-activity__source-name">{source.name}</span>
                              <span class="agent-activity__site text-xs">{site(source.url)}</span>
                            </Link>
                          </li>
                        {/each}
                      </ul>
                      {#if sources.length > SOURCE_LIMIT}
                        <button
                          type="button"
                          class="agent-activity__more text-sm font-medium"
                          onclick={() => toggle(key)}
                        >
                          {expanded.has(key)
                            ? m['chatbot.activity.collapse']()
                            : m['chatbot.activity.allSources']({ count: sources.length })}
                        </button>
                      {/if}
                    {:else if text}
                      {@render longText(key, text)}
                    {:else}
                      <p class="mb-0! text-sm text-[--text-mention-grey]">
                        {step.result?.status === 'error'
                          ? m['chatbot.activity.failed']()
                          : m['chatbot.tools.noResult']()}
                      </p>
                    {/if}
                  </div>
                {/if}
              {/each}
            </div>
          </div>
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

  .agent-activity__step {
    padding-inline-start: 2rem !important;
    padding-bottom: 0.625rem !important;
    list-style: none;
  }

  .agent-activity__step::marker {
    content: none;
  }

  /* The thread: a line from each icon down to the next one. */
  .agent-activity__step:not(:last-child)::before {
    content: '';
    position: absolute;
    top: 1.625rem;
    bottom: 0.125rem;
    left: calc(0.75rem - 0.5px);
    width: 1px;
    background: var(--border-default-grey);
  }

  .agent-activity__dot {
    position: absolute;
    top: 0;
    left: 0;
    width: 1.5rem;
    height: 1.5rem;
    color: var(--text-action-high-blue-france);
    background: var(--background-action-low-blue-france);
  }

  .agent-activity__dot:has(:global(.i-ri-error-warning-line)) {
    color: var(--text-default-error);
    background: var(--background-contrast-error);
  }

  .agent-activity__head {
    min-height: 1.5rem;
    color: var(--text-default-grey);
  }

  .agent-activity__head:hover {
    background: none;
  }

  .agent-activity__head:hover > .font-medium {
    text-decoration: underline;
  }

  .agent-activity__head :global(.agent-activity__chevron) {
    flex-shrink: 0;
    color: var(--text-mention-grey);
    transition: transform 0.15s ease;
  }

  .agent-activity__head[aria-expanded='true'] :global(.agent-activity__chevron) {
    transform: rotate(90deg);
  }

  /* The panel unfolds and folds back rather than appearing at once. Its
     rows go from 0fr to 1fr, which follows the content's height; `hidden`
     only takes effect once folded, through allow-discrete. */
  .agent-activity__panel {
    display: grid;
    grid-template-rows: 1fr;
    opacity: 1;
    transition:
      grid-template-rows 0.2s ease-out,
      opacity 0.2s ease-out,
      display 0.2s allow-discrete;
  }

  .agent-activity__panel[hidden] {
    display: none;
    grid-template-rows: 0fr;
    opacity: 0;
  }

  @starting-style {
    .agent-activity__panel:not([hidden]) {
      grid-template-rows: 0fr;
      opacity: 0;
    }
  }

  /* Room for focus rings, which the folding would otherwise cut off. */
  .agent-activity__panel-body {
    min-height: 0;
    overflow: hidden;
    margin-inline: -0.25rem;
    padding-inline: 0.25rem;
  }

  .agent-activity__request {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-mention-grey);
  }

  .agent-activity__count {
    color: var(--text-mention-grey);
  }

  .agent-activity__favicons img {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--background-default-grey);
    box-shadow: 0 0 0 2px var(--background-default-grey);
  }

  .agent-activity__favicons img + img {
    margin-inline-start: -4px;
  }

  .agent-activity__panel-body > :global(* + *) {
    padding-top: 0.75rem;
    border-top: 1px solid var(--border-default-grey);
  }

  .agent-activity__text {
    color: var(--text-default-grey);
  }

  /* A long answer shows its first lines and fades out above the button that
     shows the rest. */
  .agent-activity__text--cut {
    max-height: 9rem;
    overflow: hidden;
    mask-image: linear-gradient(#000 55%, transparent);
  }

  .agent-activity__more {
    margin-top: 0.25rem;
    color: var(--text-action-high-blue-france);
  }

  .agent-activity__more:hover {
    text-decoration: underline;
  }

  .agent-activity__panel :global(.agent-activity__source) {
    min-width: 0;
    color: var(--text-default-grey);
    --underline-img: none;
  }

  .agent-activity__panel :global(.agent-activity__source:hover > .agent-activity__source-name) {
    text-decoration: underline;
  }

  .agent-activity__source-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .agent-activity__site {
    flex-shrink: 0;
    max-width: 40%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-mention-grey);
  }

  /* On a phone the title needs the whole line. */
  @media (max-width: 36em) {
    .agent-activity__site {
      display: none;
    }
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

    .agent-activity__panel,
    .agent-activity__head :global(.agent-activity__chevron) {
      transition: none;
    }
  }
</style>
