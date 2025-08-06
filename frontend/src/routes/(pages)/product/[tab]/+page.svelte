<script lang="ts">
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import { Comparator, FAQ, History, Partners, Problem } from './components'

  const { data } = $props()
</script>

<SeoHead title={m[`seo.titles.${data.tab}`]()} />
