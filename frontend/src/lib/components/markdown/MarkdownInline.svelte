<script lang="ts">
  import { renderInlineMarkdown } from './inline'

  let { message, allowLinks = true }: { message: string; allowLinks?: boolean } = $props()
  const html = $derived(renderInlineMarkdown(message, allowLinks))
</script>

<span class="markdown-inline">{@html html}</span>
