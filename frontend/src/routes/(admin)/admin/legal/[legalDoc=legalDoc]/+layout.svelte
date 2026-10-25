<script lang="ts">
  import { resolve } from '$app/paths'
  import { PageLayout } from '$components/layout'
  import type { LegalDocumentKeys } from '$lib/generated/constants'
  import { m } from '$lib/i18n/messages'
  import type { LayoutProps } from './$types'
  const { params, children }: LayoutProps = $props()
  const kind = $derived(params.legalDoc as LegalDocumentKeys)
</script>

<PageLayout
  seoTitle={m[`admin.legal.${kind}.title`]()}
  title={m[`admin.legal.${kind}.title`]()}
  subtitle={m[`admin.legal.${kind}.subtitle`]()}
  backLink={{ href: resolve('/admin/legal'), text: m['admin.legal.back']() }}
>
  {@render children()}
</PageLayout>
