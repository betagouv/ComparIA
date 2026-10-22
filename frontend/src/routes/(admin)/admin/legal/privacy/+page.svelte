<script lang="ts">
  import { resolve } from '$app/paths'
  import LegalDocumentAdmin from '$components/admin/LegalDocumentAdmin.svelte'
  import { PageLayout } from '$components/layout'
  import { m } from '$lib/i18n/messages'
</script>

<PageLayout
  seoTitle={m['admin.legal.privacy.title']()}
  title={m['admin.legal.privacy.title']()}
  subtitle={m['admin.legal.privacy.subtitle']()}
  backLink={{ href: resolve('/admin/legal'), text: m['admin.legal.back']() }}
>
  <LegalDocumentAdmin kind="privacy_policy" />
</PageLayout>
