<script lang="ts">
  import { m } from '$lib/i18n/messages'

  let props: { title?: string; desc?: string } = $props()
  const title = $derived(props.title ? `${props.title} - ${m['seo.title']()}` : m['seo.title']())
  const desc = $derived(props.desc ?? m['seo.desc']())
</script>

<svelte:head>
  <title>{title}</title>
  <meta name="description" content={desc} />
  <meta property="og:title" content={title} />
  <meta property="og:description" content={desc} />
</svelte:head>
