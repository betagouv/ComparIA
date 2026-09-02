<script lang="ts">
  import { resolve } from '$app/paths'
  import TabNav from '$components/dsfr/TabNav.svelte'
  import PageLayout from '$components/PageLayout.svelte'
  import { m } from '$lib/i18n/messages'

  import type { LayoutProps } from './$types'

  let { children }: LayoutProps = $props()

  const links = [
    { id: 'llms' as const, icon: 'i-ri-ai-agent-line', label: 'LLMs' },
    { id: 'labs' as const, icon: 'i-ri-flask-line', label: 'Labs' },
    { id: 'licenses' as const, icon: 'i-ri-copyright-line', label: 'Licenses' },
    { id: 'endpoints' as const, icon: 'i-ri-server-line', label: 'Endpoints' }
  ].map((link) => ({ ...link, href: resolve(`/admin/llms/${link.id}`) }))
</script>

<PageLayout
  seoTitle={m['admin.llms.title']()}
  title={m['admin.llms.title']()}
  subtitle={m['admin.llms.subTitle']()}
>
  <TabNav {links} class="mb-5" />

  {@render children()}
</PageLayout>
