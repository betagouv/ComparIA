<script lang="ts">
  import { resolve } from '$app/paths'
  import { Badge, Link, Table } from '$components/dsfr'
  import { PageLayout } from '$components/layout'
  import { m } from '$lib/i18n/messages'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()

  const pages = $derived(
    (
      ['participation', 'terms', 'privacy', 'legal_notice', 'accessibility', 'ecodesign'] as const
    ).map((id) => ({
      id,
      title: m[`admin.legal.${id}.title`](),
      desc: m[`admin.legal.${id}.subtitle`](),
      href: resolve(`/admin/legal/${id}`),
      status: data.status[id]
    }))
  )
  const cols = (['title', 'desc', 'status'] as const).map((id) => ({
    id,
    label: m[`admin.legal.hub.cols.${id}`]()
  }))
</script>

<PageLayout
  seoTitle={m['admin.legal.hub.title']()}
  title={m['admin.legal.hub.title']()}
  subtitle={m['admin.legal.hub.subtitle']()}
>
  <Table caption={m['admin.legal.hub.title']()} hideCaption {cols} rows={pages}>
    {#snippet cell(page, col)}
      {#if col.id === 'title'}
        <Link href={page.href} text={page.title} size="sm" />
      {:else if col.id === 'status'}
        {#if page.status.published}
          <Badge size="sm" text={m['admin.legal.hub.published']()} variant="green" />
          {#if page.status.missing_locales}
            <Badge size="sm" text={m['form.missing_locales']()} variant="yellow" />
          {/if}
        {:else}
          <Badge size="sm" text={m['admin.legal.hub.toComplete']()} variant="red" />
        {/if}
      {:else}
        {page[col.id]}
      {/if}
    {/snippet}
  </Table>
</PageLayout>
