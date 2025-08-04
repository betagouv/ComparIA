<script lang="ts">
  import FaqContent from '$lib/components/FAQContent.svelte'
  import SeoHead from '$lib/components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
</script>

<SeoHead title={m['seo.titles.faq']()} />

<FaqContent></FaqContent>
