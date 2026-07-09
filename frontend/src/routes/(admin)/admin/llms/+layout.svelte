<script lang="ts">
  import { resolve } from '$app/paths'
  import TabNav from '$components/dsfr/TabNav.svelte'
  import PageLayout from '$components/PageLayout.svelte'
  import { m } from '$lib/i18n/messages'

  import type { LayoutProps } from './$types'

  let { children }: LayoutProps = $props()

  const links = [
    { id: 'list', icon: 'i-ri-ai-agent-line', label: 'LLMs', href: resolve('/admin/llms/list') }
  ]
</script>

<PageLayout
  seoTitle={m['admin.llms.title']()}
  title={m['admin.llms.title']()}
  subtitle={m['admin.llms.subTitle']()}
>
  <TabNav {links} class="mb-5" />

  {@render children()}
</PageLayout>
