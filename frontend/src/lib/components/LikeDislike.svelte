<script lang="ts">
  import IconButton from '$lib/components/IconButton.svelte'
  import { m } from '$lib/i18n/messages'
  import ThumbDownActive from '$lib/icons/ThumbDownActive.svelte'
  import ThumbDownDefault from '$lib/icons/ThumbDownDefault.svelte'
  import ThumbDownDisabled from '$lib/icons/ThumbDownDisabled.svelte'
  import ThumbUpActive from '$lib/icons/ThumbUpActive.svelte'
  import ThumbUpDefault from '$lib/icons/ThumbUpDefault.svelte'
  import ThumbUpDisabled from '$lib/icons/ThumbUpDisabled.svelte'

  let {
    onLikeDislikeSelected,
    disabled = false
  }: { onLikeDislikeSelected: (selected: 'like' | 'dislike' | null) => void; disabled?: boolean } =
    $props()

  let selected: 'like' | 'dislike' | null = $state(null)
</script>

<IconButton
  {disabled}
  border={true}
  Icon={disabled ? ThumbUpDisabled : selected === 'like' ? ThumbUpActive : ThumbUpDefault}
  label={m[`vote.like.${selected === 'like' ? 'selectedLabel': 'label'}`]()}
  highlight={selected === 'like'}
  on:click={() => {
    if (selected === 'like') {
      selected = null // Unselect the "like"
      onLikeDislikeSelected(selected) // Notify that no action is selected
    } else {
      selected = 'like' // Select the "like"
      onLikeDislikeSelected(selected) // Notify that "like" was selected
    }
  }}
/>

<IconButton
  {disabled}
  border={true}
  Icon={disabled ? ThumbDownDisabled : selected === 'dislike' ? ThumbDownActive : ThumbDownDefault}
  label={m[`vote.dislike.${selected === 'dislike' ? 'selectedLabel': 'label'}`]()}
  highlight={selected === 'dislike'}
  on:click={() => {
    if (selected === 'dislike') {
      selected = null // Unselect the "dislike"
      onLikeDislikeSelected(selected) // Notify that no action is selected
    } else {
      selected = 'dislike' // Select the "dislike"
      onLikeDislikeSelected(selected) // Notify that "dislike" was selected
    }
  }}
/>
