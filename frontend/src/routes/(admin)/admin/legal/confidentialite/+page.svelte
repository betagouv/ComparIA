<script lang="ts">
  import { resolve } from '$app/paths'
  import LegalDocumentAdmin from '$components/admin/LegalDocumentAdmin.svelte'
  import PageLayout from '$components/PageLayout.svelte'
  import { m } from '$lib/i18n/messages'
</script>

<PageLayout
  seoTitle={m['admin.legal.privacy.title']()}
  title={m['admin.legal.privacy.title']()}
  subtitle={m['admin.legal.privacy.subtitle']()}
>
  <p class="fr-mb-6v">
    <a class="fr-link fr-icon-arrow-left-line fr-link--icon-left" href={resolve('/admin/legal')}>
      {m['admin.legal.back']()}
    </a>
  </p>
  <LegalDocumentAdmin kind="privacy_policy" />
</PageLayout>
