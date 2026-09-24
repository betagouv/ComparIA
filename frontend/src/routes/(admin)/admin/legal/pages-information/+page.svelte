<script lang="ts">
  import { resolve } from '$app/paths'
  import InformationalLegalPagesAdmin from '$components/admin/InformationalLegalPagesAdmin.svelte'
  import PageLayout from '$components/PageLayout.svelte'
  import { m } from '$lib/i18n/messages'
</script>

<PageLayout
  seoTitle={m['admin.legal.informational.title']()}
  title={m['admin.legal.informational.title']()}
  subtitle={m['admin.legal.informational.subtitle']()}
>
  <p class="fr-mb-6v">
    <a class="fr-link fr-icon-arrow-left-line fr-link--icon-left" href={resolve('/admin/legal')}>
      {m['admin.legal.back']()}
    </a>
  </p>
  <InformationalLegalPagesAdmin />
</PageLayout>
