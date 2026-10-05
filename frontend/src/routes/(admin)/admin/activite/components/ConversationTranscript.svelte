<script lang="ts">
  import { Alert, Badge, Button } from '$components/dsfr'
  import { MarkdownCode as Markdown } from '$components/markdown'
  import type { ActivityConversation } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { CHOICE_COLORS, answerOf, label, modelName } from '../filters'
  import TagChips from './TagChips.svelte'

  let { conversation }: { conversation: ActivityConversation } = $props()

  // Text flagged as personal data stays out of sight until asked for, so it
  // does not land on a screen someone else is looking at.
  let shown = $state(false)
  const hidden = $derived(conversation.contains_pii && !shown)

  const secondsFormatter = new Intl.NumberFormat(getLocale(), { maximumFractionDigits: 1 })
  const numberFormatter = new Intl.NumberFormat(getLocale())

  const decisionLabels: Record<string, string> = {
    pass: m['admin.promptChecks.stats.decision.pass'](),
    logged: m['admin.promptChecks.stats.decision.logged'](),
    warned: m['admin.promptChecks.stats.decision.warned'](),
    blocked: m['admin.promptChecks.stats.decision.blocked'](),
    error: m['admin.promptChecks.stats.decision.error']()
  }
</script>

{#if hidden}
  <Alert variant="warning" title={m['admin.activity.conversation.piiWarning']()} class="mb-4">
    <Button
      size="sm"
      variant="secondary"
      text={m['admin.activity.conversation.show']()}
      class="mt-2"
      onclick={() => (shown = true)}
    />
  </Alert>
{/if}

<div class={['gap-8 flex flex-col', { 'blur-md select-none': hidden }]} inert={hidden}>
  {#each conversation.turns as turn, index (turn.id)}
    <article class="gap-3 flex flex-col" aria-labelledby="turn-{turn.id}">
      <div class="gap-3 flex items-start justify-end">
        <h3 id="turn-{turn.id}" class="sr-only">
          {m['admin.activity.conversation.prompt']({ index: index + 1 })}
        </h3>
        <p class="mb-0! px-5 py-3 rounded-2xl bg-light-primary md:max-w-3/4 whitespace-pre-wrap">
          {turn.prompt}
        </p>
      </div>

      <div class="gap-4 md:grid-cols-2 grid grid-cols-1">
        {#each ['a', 'b'] as const as side (side)}
          {@const view = answerOf(turn, side)}
          <section
            class={[
              'rounded-lg cg-border bg-white flex flex-col',
              view.verdict === 'preferred' && 'outline-green outline-2 -outline-offset-2',
              view.verdict === 'rejected' && 'outline-red outline-2 -outline-offset-2'
            ]}
            aria-label={modelName(conversation, side)}
          >
            <header class="px-4 py-2 gap-2 flex items-center">
              <span class="c-bot-disk-{side} shrink-0"></span>
              <span class="fr-text--sm mb-0! font-bold min-w-0 flex-1 truncate">
                {modelName(conversation, side)}
              </span>
              {#if view.verdict === 'preferred' || view.verdict === 'rejected'}
                <Badge
                  size="sm"
                  noTooltip
                  variant={view.verdict === 'preferred' ? 'green' : 'red'}
                  text={m[`admin.activity.verdicts.${view.verdict}`]()}
                />
              {/if}
            </header>

            <!-- Long answers scroll inside their box, as in the arena, so both
                 stay side by side. Focusable, or a keyboard cannot scroll it. -->
            <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
            <div
              class="px-4 text-sm max-h-80 overflow-y-auto"
              tabindex="0"
              role="group"
              aria-label={modelName(conversation, side)}
            >
              {#if view.answer}
                <Markdown message={view.answer.content} chatbot />
              {:else}
                <p class="text-[--text-mention-grey]">
                  {m['admin.activity.conversation.noAnswer']()}
                </p>
              {/if}
            </div>

            <footer class="px-4 py-2 gap-2 bg-very-light-grey rounded-b-lg mt-auto flex flex-col">
              {#if view.answer}
                <span class="text-xs text-[--text-mention-grey] tabular-nums">
                  {view.answer.duration_ms != null
                    ? `${secondsFormatter.format(view.answer.duration_ms / 1000)} s`
                    : ''}
                  {view.answer.tokens != null
                    ? ` · ${numberFormatter.format(view.answer.tokens)} ${m['admin.activity.conversation.tokens']()}`
                    : ''}
                </span>
              {/if}
              <TagChips keys={view.tags} />
              {#if view.comment}
                <p class="mb-0! text-sm gap-1.5 flex italic">
                  <span class="i-ri-chat-quote-line mt-0.5 shrink-0 text-[--text-mention-grey]"
                  ></span>
                  {view.comment}
                </p>
              {/if}
            </footer>
          </section>
        {/each}
      </div>

      <p class="mb-0! text-sm gap-x-3 gap-y-1 flex flex-wrap items-center justify-center">
        {#if turn.choice}
          <span class="gap-1.5 flex items-center">
            <span class="size-2.5 rounded-full" style:background={CHOICE_COLORS[turn.choice]}
            ></span>
            {m['admin.activity.conversation.vote']({ choice: label('choices', turn.choice) })}
          </span>
        {:else}
          <span class="text-[--text-mention-grey]">{label('choices', 'none')}</span>
        {/if}
        {#if turn.prompt_check && turn.prompt_check.decision !== 'pass'}
          <Badge
            size="sm"
            variant="yellow"
            noTooltip
            text="{decisionLabels[turn.prompt_check.decision] ??
              turn.prompt_check.decision}{Object.keys(turn.prompt_check.triggered).length
              ? ` : ${Object.keys(turn.prompt_check.triggered).join(', ')}`
              : ''}"
          />
        {/if}
      </p>
    </article>
  {/each}
</div>
