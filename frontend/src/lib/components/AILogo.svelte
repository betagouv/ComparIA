<script lang="ts">
  import type { HTMLImgAttributes } from 'svelte/elements'

  const {
    logo,
    size = 'md',
    ...props
  }: { logo: string; alt: string; size?: 'sm' | 'md' | 'lg' } & HTMLImgAttributes = $props()
  const sizeClass = $derived(
    { sm: 'w-[14px] h-[14px]', md: 'w-[20px] h-[20px]', lg: 'w-[34px] h-[34px]' }[size]
  )
  const inverted = $derived(
    ['openai.svg', 'xai.svg', 'liquid.svg', 'moonshot-ai.webp'].includes(logo) ? 'dark:invert' : ''
  )
</script>

{#if logo.includes('.')}
  <img
    {...props}
    src="/orgs/ai/{logo}"
    class={['object-contain', sizeClass, inverted, props.class]}
  />
{:else}
  <span class={[`i-ai-${logo}`, sizeClass, props.class]}></span>
{/if}
