<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import type { AgentTraceToolCall, AgentTraceToolResult } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import { isSafeWebSource } from '$lib/utils/commons'

  export type ToolActivityProps = {
    id: string
    call: AgentTraceToolCall
    result: AgentTraceToolResult | null
    /** False while the model is still answering: nothing is settled yet. */
    finished: boolean
  }

  let { id, call, result, finished }: ToolActivityProps = $props()

  function getSourceFavicon(source: { url: string; favicon?: string | null }) {
    if (source.favicon && isSafeWebSource(source.favicon)) return source.favicon
    try {
      const fallback = new URL('/favicon.ico', source.url).href
      return isSafeWebSource(fallback) ? fallback : null
    } catch {
      return null
    }
  }

  function hideBrokenFavicon(event: Event) {
    const image = event.currentTarget
    if (image instanceof HTMLImageElement) image.hidden = true
  }

  const sources = $derived.by(() => {
    const uniqueSources: { url: string; name: string; favicon: string | null }[] = []
    for (const source of result?.results ?? []) {
      const url = source.url
      if (
        url &&
        isSafeWebSource(url) &&
        !uniqueSources.some((candidate) => candidate.url === url)
      ) {
        uniqueSources.push({
          url,
          name: source.name || url,
          favicon: getSourceFavicon({ url, favicon: source.favicon })
        })
      }
    }
    return uniqueSources
  })

  const requestSummary = $derived.by(() => {
    const args = call.arguments
    if (!args) return null
    const preferredKeys = ['query', 'request', 'subject', 'name', 'title', 'url']
    const values = [
      ...preferredKeys.filter((key) => key in args).map((key) => args[key]),
      ...Object.entries(args)
        .filter(([key]) => !preferredKeys.includes(key))
        .map(([, value]) => value)
    ]
    const readable = values.find(
      (value) => ['string', 'number', 'boolean'].includes(typeof value) && String(value).trim()
    )
    return readable == null ? null : String(readable)
  })

  const resultSummary = $derived.by(() => {
    if (!result || sources.length > 0) return null
    const sourceContent = (result.results ?? [])
      .map((source) => source.content || source.name)
      .filter(Boolean)
      .join('\n')
      .trim()
    if (sourceContent) return sourceContent

    const content = result.content.trim()
    if (!content || content === '{}') return null
    try {
      const parsed = JSON.parse(content)
      if (typeof parsed === 'string') return parsed
      if (parsed && typeof parsed === 'object') {
        for (const key of ['answer', 'result', 'content', 'text', 'message']) {
          if (typeof parsed[key] === 'string') return parsed[key]
        }
        return null
      }
    } catch {
      return content
    }
    return null
  })

  const resultCountLabel = $derived(
    sources.length === 1
      ? m['chatbot.tools.result']()
      : m['chatbot.tools.results']({ count: sources.length })
  )
</script>

{#if call.name === 'web_search' && sources.length > 0}
  <details class="tool-activity-card cg-border my-3 rounded-lg bg-white w-full overflow-hidden">
    <summary class="tool-activity-summary gap-2 px-3 py-2 text-sm flex cursor-pointer items-center">
      <Icon icon="i-ri-global-line" size="sm" class="text-primary shrink-0" />
      <span class="gap-x-2 min-w-0 flex grow items-baseline">
        <span id="{id}-title" class="font-medium shrink-0 whitespace-nowrap"
          >{call.label || call.name}</span
        >
        {#if requestSummary}
          <span class="min-w-0 truncate whitespace-nowrap text-[--text-mention-grey]">
            «&nbsp;{requestSummary}&nbsp;»
          </span>
        {/if}
      </span>
      <span class="text-xs shrink-0 text-[--text-mention-grey]">{resultCountLabel}</span>
      <span class="tool-activity-chevron flex shrink-0" aria-hidden="true">
        <Icon icon="i-ri-arrow-down-s-line" size="sm" />
      </span>
    </summary>
    <div class="tool-activity-content px-4 py-3 border-t border-[--border-default-grey]">
      <ul class="my-0! p-0! text-sm list-none!">
        {#each sources as source (source.url)}
          <li class="gap-2 mb-1 last:mb-0 flex items-start">
            {#if source.favicon}
              <img
                aria-hidden="true"
                alt=""
                src={source.favicon}
                loading="lazy"
                onerror={hideBrokenFavicon}
                class="mt-0.5 h-[14px] w-[14px] shrink-0"
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
    </div>
  </details>
{:else}
  <section
    class="tool-activity-card cg-border my-3 rounded-lg bg-white w-full overflow-hidden"
    aria-labelledby="{id}-title"
  >
    <div class="gap-2 px-3 py-2 text-sm flex items-center">
      <Icon
        icon={call.name === 'web_search' ? 'i-ri-global-line' : 'i-ri-tools-line'}
        size="sm"
        class="text-primary shrink-0"
      />
      <span class="gap-x-2 min-w-0 sm:flex grow items-baseline">
        <h4 id="{id}-title" class="mb-0! text-base! font-medium! shrink-0">
          {call.label || call.name}
        </h4>
        {#if requestSummary}
          <span class="sm:inline block truncate text-[--text-mention-grey]">
            «&nbsp;{requestSummary}&nbsp;»
          </span>
        {/if}
      </span>
      {#if !result}
        <span class="text-sm shrink-0 text-[--text-mention-grey]" aria-live="polite">
          {finished ? m['chatbot.tools.noResult']() : m['chatbot.tools.running']()}
        </span>
      {:else if sources.length === 0 && !resultSummary}
        <span class="text-sm shrink-0 text-[--text-mention-grey]">
          {result.status === 'success' ? m['chatbot.tools.done']() : m['chatbot.tools.noResult']()}
        </span>
      {/if}
    </div>

    {#if resultSummary}
      <p
        class="mt-0! mb-0! px-4 py-3 text-sm border-t border-[--border-default-grey] whitespace-pre-line"
      >
        {resultSummary}
      </p>
    {/if}
  </section>
{/if}

<style>
  .tool-activity-summary {
    list-style: none;
  }

  .tool-activity-summary::-webkit-details-marker {
    display: none;
  }

  .tool-activity-chevron {
    transition: transform 150ms ease-out;
  }

  .tool-activity-card {
    interpolate-size: allow-keywords;
  }

  .tool-activity-card::details-content {
    block-size: 0;
    overflow: hidden;
    opacity: 0;
    transition:
      block-size 180ms ease-out,
      opacity 120ms ease-out,
      content-visibility 180ms allow-discrete;
  }

  .tool-activity-card[open]::details-content {
    block-size: auto;
    opacity: 1;
  }

  details[open] .tool-activity-chevron {
    transform: rotate(180deg);
  }

  @media (prefers-reduced-motion: reduce) {
    .tool-activity-chevron {
      transition: none;
    }

    .tool-activity-card::details-content {
      transition: none;
    }
  }
</style>
