<script lang="ts">
  import { Icon } from '$components/dsfr'
  import { MarkdownInline } from '$components/markdown'
  import { getAuthContext } from '$lib/auth.svelte'
  import { getLocalesContext } from '$lib/global.svelte'

  // Unlike the other home texts there is no built-in banner: an instance that
  // wrote none shows nothing.
  const banner = getLocalesContext().pickTranslation(getAuthContext().config.home_banner)
</script>

{#if banner}
  <div
    role="note"
    class="px-4 py-3 md:px-6 gap-3 text-sm flex border-b border-[--warning-850-200] bg-[--warning-975-75]"
  >
    <Icon icon="error-warning-line" size="sm" class="mt-[2px] shrink-0 text-[--warning-425-625]" />
    <p class="mb-0! m-auto max-w-[860px]">
      <MarkdownInline message={banner} />
    </p>
  </div>
{/if}
