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
  import { m } from '$lib/i18n/messages'
  import { VoteAnnotate } from '.'
  import AgentTrace from './AgentTrace.svelte'
  import type { APITrace } from './toolActivity'

  export type MessageBotProps = {
    id: string
    turnSide: ComparisonTurnSide
    bot: Bot
    choice: TurnChoice | null
    disabled?: boolean
    onVoteAnnotate: (data: Omit<APIVoteAnnotate, 'turn_id'>) => void
  }

  let { id, turnSide, bot, choice, disabled = false, onVoteAnnotate }: MessageBotProps = $props()

  const prefKind = $derived.by(() => {
    if (!choice || choice == 'idk') return null
    return choice == 'both_good' || choice == `${bot}_better` ? 'positive' : 'negative'
  })

  const message = $derived(turnSide.llm_msg!)

  const trace = $derived((message.agent_trace as APITrace) ?? [])
  const generating = $derived(turnSide.status === 'generating')

  let annotations = $derived({
    keyword_annotations: turnSide.keyword_annotations,
    custom_annotation: turnSide.custom_annotation
  })
</script>

<svelte:window onresize={() => (kept = null)} />

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
      {#if trace.length || message.reasoning_content}
        <AgentTrace
          {id}
          {trace}
          reasoning={message.reasoning_content ?? ''}
          pending={generating && !message.content.trim()}
        />
      {/if}

      <Markdown message={message.content} chatbot />
    </div>

    <div class="mt-5">
      {#if generating}
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
