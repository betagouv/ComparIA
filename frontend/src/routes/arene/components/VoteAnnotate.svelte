<script lang="ts">
  import Selector from '$components/Selector.svelte'
  import TextPrompt from '$components/TextPrompt.svelte'
  import type { APIReactionPref, VoteAnnotations } from '$lib/chatService.svelte'
  import { APINegativePrefs, APIPositivePrefs, PREFS_EMOJIS } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'

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

  const keywords = {
    positive: {
      label: m['vote.choices.positive.question'](),
      icon: 'thumb-up-fill',
      choices: APIPositivePrefs.map((value) => ({
        value,
        label: PREFS_EMOJIS[value] + ' ' + m[`vote.choices.positive.${value}`]()
      })) as { value: APIReactionPref; label: string }[]
    },
    negative: {
      label: m['vote.choices.negative.question'](),
      icon: 'thumb-down-fill',
      choices: APINegativePrefs.map((value) => ({
        value,
        label: PREFS_EMOJIS[value] + ' ' + m[`vote.choices.negative.${value}`]()
      })) as { value: APIReactionPref; label: string }[]
    }
  }
  const keywordChoices = $derived(keywords[kind])
</script>

<form {id} class="bg-light-info px-4 py-2 mt-auto">
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

  <Selector
    id="{id}-selector"
    kind="checkbox"
    bind:value={annotations.keyword_annotations}
    choices={keywordChoices.choices}
    multiple
    {disabled}
    containerClass="flex flex-wrap gap-3"
    choiceClass="px-3 py-2 rounded-full lh-none! has-checked:text-primary! text-[14px]! bg-white"
    onChange={() => onUpdate(annotations)}
  />
</form>
