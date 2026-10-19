<script lang="ts">
  import { SeoHead } from '$components/layout'
  import { MarkdownCode as Markdown, stripLeadingTitle } from '$components/markdown'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import type { InformationalPageKey } from '$lib/informational-pages.svelte'
  import type { PageProps } from './$types'

  const { data, params }: PageProps = $props()

  const title = $derived<string>(m[`seo.titles.${params.infoPage as InformationalPageKey}`]())
</script>

<SeoHead {title} />

<div class="py-10 lg:py-15">
  <div class="fr-container">
    <h1 id="main-title" class="mb-8!">{title}</h1>
    {#if data.page}
      <!-- The backend serves the default document when the requested locale has none,
      so say it rather than passing the substitution off as a translation. -->
      {#if data.page.locale !== getLocale()}
        <p class="fr-alert fr-alert--info mb-4!">{m['general.document.frenchOnly']()}</p>
      {/if}
      <Markdown message={stripLeadingTitle(data.page.content)} sanitize_html variant="document" />
    {:else}
      <p class="fr-alert fr-alert--error" role="alert">{m['general.document.unavailable']()}</p>
    {/if}
  </div>
</div>
