<script lang="ts">
  import { PageLayout } from '$components/layout'
  import { m } from '$lib/i18n/messages'

  import type { LayoutProps } from './$types'

  let { children }: LayoutProps = $props()
</script>

<PageLayout
  seoTitle={m['admin.selectionModes.title']()}
  title={m['admin.selectionModes.title']()}
  subtitle={m['admin.selectionModes.subtitle']()}
>
  {@render children()}
</PageLayout>
