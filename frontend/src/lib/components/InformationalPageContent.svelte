<script lang="ts">
  import { MarkdownCode as Markdown, stripLeadingTitle } from '$components/markdown'

  const { content }: { content: string } = $props()
</script>

<Markdown message={stripLeadingTitle(content)} sanitize_html variant="document" />
