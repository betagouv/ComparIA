<script lang="ts">
  import type { HTMLImgAttributes } from 'svelte/elements'

  const {
    iconPath,
    size = 'md',
    ...props
  }: { iconPath: string; alt: string; size?: 'sm' | 'md' | 'lg' } & HTMLImgAttributes = $props()
  const sizeClass = $derived(
    { sm: 'w-[14px] h-[14px]', md: 'w-[20px] h-[20px]', lg: 'w-[34px] h-[34px]' }[size]
  )
  const inverted = $derived(
    ['openai.svg', 'xai.svg', 'liquid.svg', 'moonshot-ai.webp'].includes(iconPath)
      ? 'dark:invert'
      : ''
  )
</script>

{#if iconPath.includes('.')}
  <img
    {...props}
    src="/orgs/ai/{iconPath}"
    class={['object-contain', sizeClass, inverted, props.class]}
  />
{:else}
  <span class={[`i-ai-${iconPath}`, sizeClass, props.class]}></span>
{/if}
