<script lang="ts">
  import Copy from '$components/Copy.svelte'
  import { Icon } from '$components/dsfr'
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import Pending from '$components/Pending.svelte'
  import type {
    APIVoteAnnotate,
    Bot,
    ComparisonTurnSide,
    TurnChoice
  } from '$lib/chatService.svelte'
  import { isAdmin } from '$lib/auth.svelte'
  import type { AgentTraceToolResult } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'
  import { AgentTrace, ToolActivity, VoteAnnotate } from '.'
  import { SvelteMap } from 'svelte/reactivity'

  export type MessageBotProps = {
    id: string
    prompt: string
    turnSide: ComparisonTurnSide
    bot: Bot
    choice: TurnChoice | null
    disabled?: boolean
    onVoteAnnotate: (data: Omit<APIVoteAnnotate, 'turn_id'>) => void
  }

  let {
    id,
    prompt,
    turnSide,
    bot,
    choice,
    disabled = false,
    onVoteAnnotate
  }: MessageBotProps = $props()

  const prefKind = $derived.by(() => {
    if (!choice || choice == 'idk') return null
    return choice == 'both_good' || choice == `${bot}_better` ? 'positive' : 'negative'
  })

  const message = $derived(turnSide.llm_msg!)

  const trace = $derived(message.agent_trace ?? [])
  const toolResults = $derived.by(() => {
    const results = new SvelteMap<string, AgentTraceToolResult>()
    for (const event of trace) {
      if (event.type === 'tool_result') results.set(event.tool_call_id, event)
    }
    return results
  })
  const latestTracedReasoning = $derived.by(() => {
    let latest = ''
    for (const event of trace) {
      if (event.type === 'reasoning') latest = event.content
    }
    return latest.trim()
  })
  const liveReasoning = $derived.by(() => {
    const reasoning = message.reasoning_content?.trim() ?? ''
    return reasoning === latestTracedReasoning ? '' : reasoning
  })

  let annotations = $derived({
    keyword_annotations: turnSide.keyword_annotations,
    custom_annotation: turnSide.custom_annotation
  })
</script>

{#snippet reasoningBlock(content: string, controlsId: string, inProgress = false)}
  <details class="reasoning-activity cg-border my-3 rounded-lg bg-white w-full overflow-hidden">
    <summary
      class="reasoning-activity-summary gap-2 px-3 py-2 text-sm flex cursor-pointer items-center"
    >
      <Icon icon="i-ri-brain-2-line" size="sm" class="text-primary shrink-0" />
      <span class="font-medium grow" aria-live={inProgress ? 'polite' : undefined}>
        {inProgress ? m['chatbot.reasoning.inProgress']() : m['chatbot.reasoning.finished']()}
      </span>
      <span class="reasoning-activity-chevron flex shrink-0" aria-hidden="true">
        <Icon icon="i-ri-arrow-down-s-line" size="sm" />
      </span>
    </summary>
    <div
      id={controlsId}
      class="reasoning-activity-content px-3 py-2 text-sm border-t border-[--border-default-grey] text-[--text-mention-grey]"
    >
      {@html sanitize(content.split('\n').join('<br>'))}
    </div>
  </details>
{/snippet}

<div class="md:w-full md:min-w-0 md:flex-1 flex w-[80vw] flex-col">
  <div
    class={[
      'message-bot cg-border rounded-lg! bg-white flex h-full flex-col',
      {
        'outline-2 -outline-offset-2': !!prefKind,
        'outline-red': prefKind === 'negative',
        'outline-green': prefKind === 'positive'
      }
    ]}
  >
    <div class="px-4 py-2 flex items-center">
      <div class="c-bot-disk-{bot}"></div>
      <h3 class="ms-2! mb-0! text-sm! me-auto">{m[`models.names.${bot}`]()}</h3>
      <Copy value={message.content} />
    </div>

    <!-- Long answers scroll inside this box. Without a tab stop, a keyboard
         user cannot reach the part below the fold. -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div
      class="px-4 overflow-scroll"
      tabindex="0"
      role="group"
      aria-label={m[`models.names.${bot}`]()}
    >
      {#if isAdmin() && message.agent_trace?.length}
        <AgentTrace id="{id}-agent-trace" {prompt} events={message.agent_trace} />
      {/if}

      {#each trace as event, index (`${event.type}-${index}`)}
        {#if event.type === 'reasoning'}
          {@render reasoningBlock(event.content, `reasoning-${message.generation_id}-${index}`)}
        {:else if event.type === 'intermediate_content'}
          <Markdown message={event.content} chatbot />
        {:else if event.type === 'tool_call'}
          <ToolActivity
            id="{id}-tool-activity-{index}"
            call={event}
            result={toolResults.get(event.tool_call_id) ?? null}
            finished={turnSide.status !== 'generating'}
          />
        {/if}
      {/each}

      {#if liveReasoning}
        {@render reasoningBlock(
          liveReasoning,
          `reasoning-${message.generation_id}-live`,
          turnSide.status === 'generating' && !message.content
        )}
      {/if}

      <Markdown message={message.content} chatbot />
    </div>

    <div class="mt-5">
      {#if turnSide.status === 'generating'}
        <Pending message={m['chatbot.loading']()} />
      {/if}
    </div>

    {#if prefKind}
      <VoteAnnotate
        id="vote-annotate-{id}"
        bind:annotations
        kind={prefKind}
        {disabled}
        onUpdate={(annotations) => onVoteAnnotate({ pos: bot, ...annotations })}
      />
    {/if}
  </div>
</div>

<style>
  .reasoning-activity-summary {
    list-style: none;
  }

  .reasoning-activity-summary::-webkit-details-marker {
    display: none;
  }

  .reasoning-activity-chevron {
    transition: transform 150ms ease-out;
  }

  .reasoning-activity {
    interpolate-size: allow-keywords;
  }

  .reasoning-activity::details-content {
    block-size: 0;
    overflow: hidden;
    opacity: 0;
    transition:
      block-size 180ms ease-out,
      opacity 120ms ease-out,
      content-visibility 180ms allow-discrete;
  }

  .reasoning-activity[open]::details-content {
    block-size: auto;
    opacity: 1;
  }

  details[open] .reasoning-activity-chevron {
    transform: rotate(180deg);
  }

  @media (prefers-reduced-motion: reduce) {
    .reasoning-activity-chevron {
      transition: none;
    }

    .reasoning-activity::details-content {
      transition: none;
    }
  }
</style>
