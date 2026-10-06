<script lang="ts">
  import { getVoteTagsContext, voteTagLabel } from '$lib/voteTags'

  let { keys }: { keys: string[] } = $props()

  const tags = getVoteTagsContext()
  const chips = $derived(
    keys.map((key) => {
      const tag = tags.find((tag) => tag.key === key)
      return tag
        ? { key, emoji: tag.emoji, label: voteTagLabel(tag), sign: tag.sign }
        : { key, emoji: '•', label: key, sign: null }
    })
  )
</script>

{#if chips.length}
  <ul class="gap-1 m-0! p-0! flex list-none flex-wrap">
    {#each chips as chip (chip.key)}
      <!-- The same pair as the ranking's preference table: praise on green,
           criticism on the warning tint, and the emoji says it without colour. -->
      <li
        class={[
          'text-xs px-2 py-0.5 rounded-full',
          chip.sign === 'positive' &&
            'bg-[--green-emeraude-975-75] text-[--green-emeraude-sun-425-moon-753]',
          chip.sign === 'negative' && 'bg-[--warning-950-100] text-[--warning-425-625]',
          !chip.sign && 'bg-[--background-contrast-grey] text-[--text-mention-grey]'
        ]}
      >
        {chip.emoji}
        {chip.label}
      </li>
    {/each}
  </ul>
{/if}
