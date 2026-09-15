<script lang="ts">
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import { stripLeadingTitle } from '$components/markdown/headings'

  const { content }: { content: string } = $props()
</script>

<Markdown message={stripLeadingTitle(content)} sanitize_html variant="document" />
