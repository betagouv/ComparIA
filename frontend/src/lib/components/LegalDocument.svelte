<script lang="ts">
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import { stripLeadingTitle } from '$components/markdown/headings'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'

  let { version, effectiveAt, content }: { version: string; effectiveAt: string; content: string } =
    $props()

  // Legal timestamps have no offset, so both sides read them as local time and
  // render the same day.
  const date = $derived(
    new Date(effectiveAt).toLocaleDateString(getLocale(), {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  )
</script>

<p class="fr-text--sm text-grey">{m['general.document.version']({ version, date })}</p>

<Markdown message={stripLeadingTitle(content)} sanitize_html variant="document" />
