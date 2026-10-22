<script lang="ts">
  import { resolve } from '$app/paths'
  import LegalDocumentAdmin from '$components/admin/LegalDocumentAdmin.svelte'
  import { PageLayout } from '$components/layout'
  import { m } from '$lib/i18n/messages'
</script>

<PageLayout
  seoTitle={m['admin.legal.terms.title']()}
  title={m['admin.legal.terms.title']()}
  subtitle={m['admin.legal.terms.subtitle']()}
  backLink={{ href: resolve('/admin/legal'), text: m['admin.legal.back']() }}
>
  <LegalDocumentAdmin kind="terms" />
</PageLayout>
