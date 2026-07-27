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
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'
  import { AgentTrace, VoteAnnotate, WebSearchResults } from '.'

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

  let annotations = $derived({
    keyword_annotations: turnSide.keyword_annotations,
    custom_annotation: turnSide.custom_annotation
  })
</script>

<div class="md:w-full flex w-[80vw] flex-col">
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
      <h2 class="ms-2! mb-0! text-sm! me-auto">{m[`models.names.${bot}`]()}</h2>
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
      {#if message.agent_trace?.length}
        <AgentTrace id="{id}-agent-trace" {prompt} events={message.agent_trace} />
      {/if}


      {#if message.reasoning_content?.trim()}
        <section class="fr-accordion mb-8 py-2">
          <div class="fr-highlight ms-0! ps-0!">
            <h3 class="fr-accordion__title ms-1!">
              <button
                type="button"
                class="fr-accordion__btn text-primary! bg-transparent!"
                aria-expanded="true"
                aria-controls="reasoning-{message.generation_id}"
              >
                <Icon icon="i-ri-brain-2-line" class="text-primary me-1" />
                {#if message.content === '' && turnSide.status === 'generating'}
                  {m['chatbot.reasoning.inProgress']()}
                {:else}
                  {m['chatbot.reasoning.finished']()}
                {/if}
              </button>
            </h3>
            <div
              id="reasoning-{message.generation_id}"
              class="fr-collapse m-0! p-0! text-sm text-[#8B8B8B]"
            >
              <div class="px-5 py-4">
                {@html sanitize(message.reasoning_content.split('\n').join('<br>'))}
              </div>
            </div>
          </div>
        </section>
      {/if}

      {#if message.web_search_results?.length}
        <WebSearchResults id="{id}-web-search-results" results={message.web_search_results} />
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
