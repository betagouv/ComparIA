<script lang="ts">
  import Copy from '$components/Copy.svelte'
  import { MarkdownCode as Markdown } from '$components/markdown'
  import Pending from '$components/Pending.svelte'
  import type {
    APIVoteAnnotate,
    Bot,
    ComparisonTurnSide,
    TurnChoice
  } from '$lib/chatService.svelte'
  import { isAdmin } from '$lib/authContext.svelte'
  import type { AgentTraceToolResult } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import { AgentActivity, AgentTrace, VoteAnnotate } from '.'
  import { SvelteMap } from 'svelte/reactivity'
  import type { ActivityStep } from './toolActivity'

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
  const generating = $derived(turnSide.status === 'generating')

  // Reasoning and tool calls that follow each other read as one line of
  // activity; text the model wrote between them stays in the answer.
  type Block = { type: 'text'; content: string } | { type: 'activity'; steps: ActivityStep[] }
  const blocks = $derived.by(() => {
    const results = new SvelteMap<string, AgentTraceToolResult>()
    for (const event of trace) {
      if (event.type === 'tool_result') results.set(event.tool_call_id, event)
    }

    const blocks: Block[] = []
    const addStep = (step: ActivityStep) => {
      const last = blocks.at(-1)
      if (last?.type === 'activity') last.steps.push(step)
      else blocks.push({ type: 'activity', steps: [step] })
    }
    let tracedReasoning = ''
    for (const event of trace) {
      if (event.type === 'intermediate_content') {
        blocks.push({ type: 'text', content: event.content })
      } else if (event.type === 'reasoning') {
        tracedReasoning = event.content.trim()
        addStep({ type: 'reasoning', content: event.content })
      } else if (event.type === 'tool_call') {
        addStep({ type: 'tool', call: event, result: results.get(event.tool_call_id) ?? null })
      }
    }
    // Reasoning streams before the trace records it.
    const liveReasoning = message.reasoning_content?.trim() ?? ''
    if (liveReasoning && liveReasoning !== tracedReasoning) {
      addStep({ type: 'reasoning', content: liveReasoning })
    }
    return blocks
  })
  // The last run of steps is live until the answer starts.
  const activeBlock = $derived(
    generating && !message.content.trim() && blocks.at(-1)?.type === 'activity'
      ? blocks.length - 1
      : -1
  )

  let annotations = $derived({
    keyword_annotations: turnSide.keyword_annotations,
    custom_annotation: turnSide.custom_annotation
  })
</script>

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

      {#each blocks as block, index (index)}
        {#if block.type === 'text'}
          <Markdown message={block.content} chatbot />
        {:else}
          <AgentActivity
            id="{id}-activity-{index}"
            steps={block.steps}
            active={index === activeBlock}
          />
        {/if}
      {/each}

      <Markdown message={message.content} chatbot />
    </div>

    <div class="mt-5">
      {#if generating && activeBlock === -1}
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
