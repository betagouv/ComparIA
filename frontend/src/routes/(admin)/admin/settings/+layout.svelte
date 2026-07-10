<script lang="ts">
  import { resolve } from '$app/paths'
  import TabNav from '$components/dsfr/TabNav.svelte'
  import PageLayout from '$components/PageLayout.svelte'

  import type { LayoutProps } from './$types'

  let { children }: LayoutProps = $props()

  const links = [{ id: 'authentification', icon: 'i-ri-fingerprint-line', label: 'Authentification' }].map(
    (link) => ({ ...link, href: resolve(`/admin/settings/${link.id}`) })
  )
</script>

<PageLayout seoTitle="Paramètres" title="Paramètres" subtitle="Configuration de l'application.">
  <TabNav {links} class="mb-5" />

  {@render children()}
</PageLayout>
