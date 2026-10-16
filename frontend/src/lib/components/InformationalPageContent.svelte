<script lang="ts">
  import { MarkdownCode as Markdown, stripLeadingTitle } from '$components/markdown'
  import { m } from '$lib/i18n/messages'

  const { title, content }: { title: string; content: string | null } = $props()
</script>

<div class="py-10 lg:py-15">
  <div class="fr-container">
    <h1 id="main-title" class="mb-8!">{title}</h1>
    {#if content}
      <Markdown message={stripLeadingTitle(content)} sanitize_html variant="document" />
    {:else}
      <p class="fr-alert fr-alert--error" role="alert">{m['general.document.unavailable']()}</p>
    {/if}
  </div>
</div>
