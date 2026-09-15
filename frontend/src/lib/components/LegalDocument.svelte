<script lang="ts">
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import { stripLeadingTitle } from '$components/markdown/headings'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'

  let {
    version,
    effectiveAt,
    content,
    locale
  }: { version: string; effectiveAt: string; content: string; locale: string } = $props()

  // The backend serves the French document when the requested locale has none,
  // so say it rather than passing the substitution off as a translation.
  const substituted = $derived(locale !== getLocale())

  // The date a document takes effect is one fact, not one per reader, so it is
  // pinned to the zone it is set in. Leaving it to the viewer would also make the
  // server and the browser disagree around midnight. Same zone as the backoffice.
  const date = $derived(
    new Date(effectiveAt).toLocaleDateString(getLocale(), {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      timeZone: 'Europe/Paris'
    })
  )
</script>

{#if substituted}
  <p class="fr-alert fr-alert--info">{m['general.document.frenchOnly']()}</p>
{/if}

<p class="fr-text--sm text-grey">{m['general.document.version']({ version, date })}</p>

<Markdown message={stripLeadingTitle(content)} sanitize_html variant="document" />
