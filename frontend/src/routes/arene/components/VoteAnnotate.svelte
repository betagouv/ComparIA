<script lang="ts">
  import Selector from '$components/Selector.svelte'
  import TextPrompt from '$components/TextPrompt.svelte'
  import type { VoteAnnotations } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { getVoteTagsContext, voteTagLabel, voteTagsBySign } from '$lib/voteTags'
  import { fly } from 'svelte/transition'

  export interface VoteAnnotateProps {
    id: string
    kind: 'positive' | 'negative'
    annotations: VoteAnnotations
    onUpdate: (annotations: VoteAnnotations) => void
    disabled?: boolean
  }

  let {
    id,
    kind,
    annotations = $bindable(),
    onUpdate,
    disabled = false
  }: VoteAnnotateProps = $props()

  const tags = getVoteTagsContext()

  const keywordChoices = $derived(
    voteTagsBySign(tags, kind).map((tag) => ({
      value: tag.key,
      label: tag.emoji + ' ' + voteTagLabel(tag)
    }))
  )
</script>

<form
  {id}
  class="cl-vote-annotate bg-light-info px-4 py-2 mt-auto"
  in:fly={{ y: 8, duration: 200 }}
>
  <TextPrompt
    id="chatbot-prompt"
    bind:value={annotations.custom_annotation}
    {disabled}
    label={m[`vote.choices.${kind}.comment`]()}
    placeholder={m[`vote.choices.${kind}.comment`]()}
    hideLabel
    rows={2}
    maxRows={2}
    onSubmit={() => onUpdate(annotations)}
    onBlur={() => onUpdate(annotations)}
    class="mb-2!"
  />

  <!-- An instance can turn off a whole side of the taxonomy, which leaves the
       comment box and no chips to pick from. -->
  {#if keywordChoices.length}
    <Selector
      id="{id}-selector"
      kind="checkbox"
      bind:value={annotations.keyword_annotations}
      choices={keywordChoices}
      multiple
      {disabled}
      containerClass="flex flex-wrap gap-1"
      choiceClass="px-2 py-1 md:px-3 md:py-2 rounded-full lh-none! has-checked:text-primary! text-xs! md:text-[14px]! bg-white"
      onChange={() => onUpdate(annotations)}
    />
  {/if}
</form>

<style>
  @keyframes chipPulse {
    0% {
      transform: scale(1);
    }
    50% {
      transform: scale(1.08);
    }
    100% {
      transform: scale(1);
    }
  }

  .cl-vote-annotate :global(label:has(input:checked)) {
    animation: chipPulse 220ms ease-out;
  }
</style>
