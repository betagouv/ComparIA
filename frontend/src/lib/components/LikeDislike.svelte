<script lang="ts">
  import IconButton from '$lib/components/IconButton.svelte'
  import { m } from '$lib/i18n/messages'

  export interface LikeDislikeProps {
    liked: boolean | null
    onChange: (liked: boolean | null) => void
    disabled?: boolean
  }
  let { liked = $bindable(), onChange, disabled = false }: LikeDislikeProps = $props()
</script>

<IconButton
  {disabled}
  border={true}
  icon={disabled ? 'thumb-up-line' : liked === true ? 'thumb-up-fill' : 'thumb-up-line'}
  label={m[`vote.like.${liked === true ? 'selectedLabel' : 'label'}`]()}
  highlight={liked === true}
  onclick={() => {
    liked = liked === true ? null : true
    onChange(liked)
  }}
/>

<IconButton
  {disabled}
  border={true}
  icon={disabled ? 'thumb-down-line' : liked === false ? 'thumb-down-fill' : 'thumb-down-line'}
  label={m[`vote.dislike.${liked === false ? 'selectedLabel' : 'label'}`]()}
  highlight={liked === false}
  onclick={() => {
    liked = liked === false ? null : false
    onChange(liked)
  }}
/>
