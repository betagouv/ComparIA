<script lang="ts">
  import IconButton from '$lib/components/IconButton.svelte'
  import { m } from '$lib/i18n/messages'
  import ThumbDownActive from '$lib/icons/ThumbDownActive.svelte'
  import ThumbDownDefault from '$lib/icons/ThumbDownDefault.svelte'
  import ThumbDownDisabled from '$lib/icons/ThumbDownDisabled.svelte'
  import ThumbUpActive from '$lib/icons/ThumbUpActive.svelte'
  import ThumbUpDefault from '$lib/icons/ThumbUpDefault.svelte'
  import ThumbUpDisabled from '$lib/icons/ThumbUpDisabled.svelte'

  export interface LikeDislikeProps {
    liked: boolean | null
    onChange: (liked: boolean | null) => void
    disabled?: boolean
  }
  let {
    liked = $bindable(),
    onChange,
    disabled = false
  }: LikeDislikeProps = $props()
</script>

<IconButton
  {disabled}
  border={true}
  Icon={disabled ? ThumbUpDisabled : liked === true ? ThumbUpActive : ThumbUpDefault}
  label={m[`vote.like.${liked === true ? 'selectedLabel' : 'label'}`]()}
  highlight={liked === true}
  on:click={() => {
    liked = liked === true ? null : true
    onChange(liked)
  }}
/>

<IconButton
  {disabled}
  border={true}
  Icon={disabled ? ThumbDownDisabled : liked === false ? ThumbDownActive : ThumbDownDefault}
  label={m[`vote.dislike.${liked === false ? 'selectedLabel' : 'label'}`]()}
  highlight={liked === false}
  on:click={() => {
    liked = liked === false ? null : false
    onChange(liked)
  }}
/>
