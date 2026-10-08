<script lang="ts">
  import { tryGetAuthContext } from '$lib/authContext.svelte'
  import { m } from '$lib/i18n/messages'

  let props: { title?: string; desc?: string } = $props()
  const auth = tryGetAuthContext()
  // The name comes from the admin panel and the wording around it from the
  // message files, so a renamed instance does not carry someone else's name in
  // the tab title, the search results and the social previews.
  const platformName = $derived(auth?.config?.platform_name || m['header.title']())
  const siteName = $derived(m['seo.title']({ platformName }))
  const title = $derived(props.title ? `${props.title} - ${siteName}` : siteName)
  const desc = $derived(props.desc ?? m['seo.desc']({ platformName }))
</script>

<svelte:head>
  <title>{title}</title>
  <meta name="description" content={desc} />
  <meta property="og:title" content={title} />
  <meta property="og:description" content={desc} />
</svelte:head>
