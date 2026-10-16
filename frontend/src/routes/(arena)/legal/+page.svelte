<script lang="ts">
  import InformationalPageContent from '$components/InformationalPageContent.svelte'
  import { SeoHead } from '$components/layout'
  import { m } from '$lib/i18n/messages'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()
</script>

<SeoHead title={m['seo.titles.mentions-legales']()} />

<InformationalPageContent title={m['general.legal.title']()} content={data.content} />
