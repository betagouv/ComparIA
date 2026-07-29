<script lang="ts">
  import PageLayout from '$components/PageLayout.svelte'
  import { m } from '$lib/i18n/messages'

  import type { LayoutProps } from './$types'

  let { children }: LayoutProps = $props()
</script>

<PageLayout seoTitle={m['admin.nav.tools']()} title={m['admin.nav.tools']()}>
  {@render children()}
</PageLayout>
