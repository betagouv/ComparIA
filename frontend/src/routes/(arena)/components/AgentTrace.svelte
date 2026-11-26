<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import Expandable from '$components/Expandable.svelte'
  import { MarkdownCode as Markdown } from '$components/markdown'

  import { getToolsContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { SvelteSet } from 'svelte/reactivity'
  import IconList from './IconList.svelte'
  import type {
    APITrace,
    APITraceIntermediateContent,
    APITraceReasoning,
    TraceStatus,
    WebSource
  } from './toolActivity'
  import {
    linkify,
    mergeTraceTools,
    toolName,
    toolRequest,
    toolResultText,
    webSources
  } from './toolActivity'

  let {
    id,
    trace,
    reasoning = '',
    pending = false
  }: { id: string; trace: APITrace; reasoning?: string; pending?: boolean } = $props()

  const tools = getToolsContext()

  // Long lists and answers the visitor chose to see in full.
  let expanded = new SvelteSet<string>()

  const mergedTrace = $derived(mergeTraceTools(trace, reasoning))

  type TraceItemToolChild<T> = {
    request: string | null
    function: string
    content: T | null
    status: TraceStatus
  }
  type TraceItemWebSearch = {
    type: 'web_search'
    name: string
    key: string
    children: TraceItemToolChild<WebSource[]>[]
  }
  type TraceItemTool = {
    type: 'tool'
    name: string
    key: string
    children: TraceItemToolChild<string>[]
  }
  type AnyTraceItemTool = TraceItemTool | TraceItemWebSearch
  type AnyTraceItem = APITraceReasoning | APITraceIntermediateContent | AnyTraceItemTool

  function isTool(item: AnyTraceItem): item is AnyTraceItemTool {
    return item.type === 'tool' || item.type === 'web_search'
  }

  const traceItems = $derived<AnyTraceItem[]>(
    mergedTrace.map((item) => {
      if (item.type === 'tool_call') {
        return {
          type: item.isWebSearch ? 'web_search' : 'tool',
          name: toolName(item.children[0].call),
          key: item.children[0].call.tool,
          children: item.children.map((child) => ({
            request: toolRequest(child.call),
            function: child.call.name,
            content: (item.isWebSearch ? webSources : toolResultText)(child.result),
            status: child.result?.status ?? ('pending' as const)
          }))
        } as AnyTraceItemTool
      }
      return { type: item.type, content: item.content }
    })
  )

  const ICONS = {
    reasoning: 'i-ri-brain-ai-3-line',
    intermediate_content: 'i-ri-chat-ai-3-line',
    tool: 'i-ri-tools-line',
    web_search: 'i-ri-global-line',
    search: 'i-ri-search-line',
    error: 'i-ri-error-warning-line'
  } as const
  function getIconProps(kind: keyof typeof ICONS) {
    return {
      icon: ICONS[kind],
      size: 'xs' as const,
      block: true,
      class: kind === 'search' ? 'text-grey' : kind === 'error' ? 'text-error' : 'text-primary'
    }
  }

  function getStatus(item: AnyTraceItem): TraceStatus {
    if (isTool(item)) {
      if (item.children.every((child) => ['error', 'empty'].includes(child.status))) return 'error'
      if (item.children.some((child) => child.status === 'pending')) return 'pending'
    } else if (pending) {
      if (traceItems.indexOf(item) === traceItems.length - 1) return 'pending'
    }
    return 'success'
  }

  function getToolIcons(item: AnyTraceItemTool): { icons: string[]; count?: number } {
    if (item.type === 'web_search') {
      return {
        icons: item.children
          .flatMap((child) => child.content?.map((c) => c.favicon))
          .filter((v) => typeof v === 'string')
      }
    }
    const tool = tools.all.find((tool) => tool.key === item.key)
    return {
      icons: [tool?.logo_url || tool?.icon || 'i-ri-tools-line'],
      count: item.children.length
    }
  }

  function isLong(content: string | WebSource[]) {
    if (typeof content === 'string') {
      return content.length > 400 || content.split('\n').length > 6
    } else {
      return content.length > 5
    }
  }

  function site(url: string) {
    return new URL(url).hostname.replace(/^www\./, '')
  }
</script>

{#snippet showMore(id: string, content: string | WebSource[], markdown: boolean = false)}
  {@const cut = isLong(content)}
  {@const full = expanded.has(id) || !cut}
  {#if typeof content === 'string'}
    <div class={{ 'max-h-36 overflow-hidden mask-b-from-55%': !full }}>
      {#if markdown}
        <div class="trace-markdown">
          <Markdown message={content} chatbot />
        </div>
      {:else}
        <p class={['mb-0! text-xs! break-words whitespace-pre-line']}>
          {#each linkify(content) as segment, segmentIndex (segmentIndex)}
            {#if segment.url}
              <Link href={segment.url} text={segment.text} class="text-xs!" />
            {:else}
              {segment.text}
            {/if}
          {/each}
        </p>
      {/if}
    </div>
  {:else}
    {@const sources = expanded.has(id) ? content : content.slice(0, 5)}
    <ul class="gap-1!">
      {#each sources as source (source.url)}
        <li>
          <Link
            href={source.url}
            text={source.name}
            hideExternalIcon
            class="text-grey! gap-2 text-xs! flex! w-full items-center bg-none!"
          >
            <Icon src={source.favicon} icon="i-ri-global-line" size="xs" />
            <span class="truncate">{source.name}</span>
            <span class="text-xs text-nowrap">{site(source.url)}</span>
          </Link>
        </li>
      {/each}
    </ul>
  {/if}
  {#if cut}
    <button
      type="button"
      class="text-primary mt-2 underline"
      onclick={() => (expanded.has(id) ? expanded.delete(id) : expanded.add(id))}
    >
      {full ? m['chatbot.activity.collapse']() : m['chatbot.activity.showAll']()}
    </button>
  {/if}
{/snippet}

{#snippet tool(tool: AnyTraceItemTool, i: number)}
  {#if tool.children}
    <ol>
      {#each tool.children as child, j (j)}
        {@const chilId = `trace-${id}-item-${i}-child-${j}`}
        <li>
          <Expandable id={chilId} contentClass="ps-5">
            {#snippet label()}
              <Icon {...getIconProps('search')} />
              {#if tool.type === 'web_search'}
                {m['chatbot.tools.label.web_search']({ request: child.request ?? '' })}
              {:else}
                {m['chatbot.tools.label.tool']({
                  request: child.request ?? '',
                  name: child.function
                })}
              {/if}
            {/snippet}

            {#snippet content()}
              {#if child.content}
                {@render showMore(chilId, child.content)}
              {:else if child.status === 'error'}
                {m['chatbot.activity.failed']()}
              {:else if child.status === 'empty'}
                {m['chatbot.tools.noResult']()}
              {:else}
                {m['chatbot.tools.running']()}
              {/if}
            {/snippet}
          </Expandable>
        </li>
      {/each}
    </ol>
  {/if}
{/snippet}

<Expandable
  id="trace-{id}"
  label={m['chatbot.activity.reasoning']()}
  labelClass="font-bold"
  expanded={true}
  class="px-3! py-4! mb-3 text-xs rounded-md bg-[--background-alt-grey]"
>
  {#snippet content()}
    <ol class="ms-4! b-s-1 border-[--grey-925-125]">
      {#each traceItems as item, i (i)}
        {@const itemId = `trace-${id}-item-${i}`}
        <li class="-ms-2">
          <Expandable
            id={itemId}
            class="text-black"
            labelClass="bg-[--background-alt-grey]"
            contentClass="text-grey ps-5"
          >
            {#snippet label()}
              {@const status = getStatus(item)}
              <Icon {...getIconProps(item.type)} />
              <span class={{ pending: status === 'pending' }}>
                {m[
                  `chatbot.activity.state.${item.type}.${status === 'pending' ? status : 'finished'}`
                ]({ name: item.type === 'tool' ? item.name : '' })}
              </span>

              {#if isTool(item)}
                {#if status === 'error'}
                  <Icon {...getIconProps('error')} />
                {/if}
                <IconList {...getToolIcons(item)} fallbackIcon="i-ri-tools-line" />
              {/if}
            {/snippet}

            {#snippet content()}
              {#if isTool(item)}
                {@render tool(item, i)}
              {:else}
                {@render showMore(itemId, item.content, true)}
              {/if}
            {/snippet}
          </Expandable>
        </li>
      {/each}
    </ol>
  {/snippet}
</Expandable>

<style>
  ul,
  ol {
    display: flex;
    flex-direction: column;
    gap: 8px;
    list-style: none;
    margin: unset;
    padding: unset;
    li {
      padding: unset;
      list-style: none;
      &::marker {
        content: none;
      }
    }
  }

  /* Reasoning reads smaller than the answer it leads to. */
  .trace-markdown :global(.md),
  .trace-markdown :global(.md p),
  .trace-markdown :global(.md li) {
    font-size: 12px;
  }

  /* A light band crossing the grey text while the model works, as ChatGPT
     does. It replaces a spinner, so the line keeps its height. */
  .pending {
    background: linear-gradient(
        90deg,
        var(--grey-0-1000) 0%,
        var(--grey-0-1000) 30%,
        var(--grey-625-425) 50%,
        var(--grey-0-1000) 70%,
        var(--grey-0-1000) 100%
      )
      0 0 / 250% 100%;
    background-clip: text;
    -webkit-background-clip: text;
    color: transparent;
    animation: agent-activity-shimmer 2s linear infinite;
  }

  @keyframes agent-activity-shimmer {
    from {
      background-position: 100% 0;
    }
    to {
      background-position: 0% 0;
    }
  }
</style>
