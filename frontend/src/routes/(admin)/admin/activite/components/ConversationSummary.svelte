<script lang="ts">
  import { Button } from '$components/dsfr'
  import { MarkdownCode as Markdown } from '$components/markdown'
  import type { ActivityConversation, ActivityTurn } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import { answerOf, label, modelName } from '../filters'
  import TagChips from './TagChips.svelte'
  import VerdictMark from './VerdictMark.svelte'

  let { conversation }: { conversation: ActivityConversation } = $props()

  // Text flagged as personal data stays out of sight until asked for, so it
  // does not land on a screen someone else is looking at.
  let shown = $state(false)
  const hidden = $derived(conversation.contains_pii && !shown)

  // Answers open a few lines deep: the question, the vote and the feedback
  // are what is skimmed, the full answer is one click away.
  let opened = $state<Record<string, boolean>>({})
  const LONG = 280

  const isLong = (turn: ActivityTurn) =>
    [turn.answer_a, turn.answer_b].some((answer) => (answer?.content.length ?? 0) > LONG)
</script>

{#if hidden}
  <p class="fr-text--sm mb-4! gap-3 flex flex-wrap items-center">
    <span class="i-ri-eye-off-line text-[--text-mention-grey]" aria-hidden="true"></span>
    {m['admin.activity.conversation.piiWarning']()}
    <Button
      size="sm"
      variant="tertiary"
      text={m['admin.activity.conversation.show']()}
      onclick={() => (shown = true)}
    />
  </p>
{/if}

<div class={{ 'blur-md select-none': hidden }} inert={hidden}>
  {#each conversation.turns as turn (turn.id)}
    {@const long = isLong(turn)}
    {@const open = !!opened[turn.id]}
    <article class="py-5 first:pt-0 border-t border-[--border-default-grey] first:border-t-0">
      <p class="mb-3! font-bold whitespace-pre-wrap">{turn.prompt}</p>

      <div class="gap-x-8 gap-y-4 md:grid-cols-2 grid grid-cols-1">
        {#each ['a', 'b'] as const as side (side)}
          {@const view = answerOf(turn, side)}
          <section aria-label={modelName(conversation, side)}>
            <p class="fr-text--xs mb-1! gap-1.5 flex items-center text-[--text-mention-grey]">
              <VerdictMark verdict={view.verdict} />
              <span
                class={{ 'font-bold text-[--text-default-grey]': view.verdict === 'preferred' }}
              >
                {modelName(conversation, side)}
              </span>
            </p>
            <div class={['answer text-sm', { 'answer-clamp': long && !open }]}>
              {#if view.answer}
                <Markdown message={view.answer.content} chatbot />
              {:else}
                <p class="text-[--text-mention-grey]">
                  {m['admin.activity.conversation.noAnswer']()}
                </p>
              {/if}
            </div>
            {#if view.tags.length || view.comment}
              <div class="mt-2 gap-2 flex flex-wrap items-center">
                <TagChips keys={view.tags} />
                {#if view.comment}
                  <p class="fr-text--sm mb-0! italic">« {view.comment} »</p>
                {/if}
              </div>
            {/if}
          </section>
        {/each}
      </div>

      {#if turn.choice && !turn.choice.endsWith('_better')}
        <!-- A or B winning is already on the answers; a tie or "don't know"
             is not. -->
        <p class="fr-text--xs mt-3! mb-0! text-[--text-mention-grey]">
          {m['admin.activity.conversation.vote']({ choice: label('choices', turn.choice) })}
        </p>
      {/if}

      {#if long}
        <button
          type="button"
          class="fr-text--xs mt-2! mb-0! gap-1 flex items-center text-[--text-action-high-blue-france]"
          aria-expanded={open}
          onclick={() => (opened[turn.id] = !open)}
        >
          {open
            ? m['admin.activity.conversation.readLess']()
            : m['admin.activity.conversation.readMore']()}
          <span
            class={[open ? 'i-ri-arrow-up-s-line' : 'i-ri-arrow-down-s-line']}
            aria-hidden="true"
          ></span>
        </button>
      {/if}
    </article>
  {/each}
</div>

<style>
  .answer > :global(:first-child),
  .answer > :global(:first-child > :first-child) {
    margin-top: 0;
    padding-top: 0;
  }
  .answer-clamp {
    max-height: 6.5rem;
    overflow: hidden;
    mask-image: linear-gradient(to bottom, black 60%, transparent);
  }
</style>
