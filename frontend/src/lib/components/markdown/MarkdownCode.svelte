<script lang="ts">
  // This is the base MarkdownCode component from gradio migrated to svelte 5
  // https://github.com/gradio-app/gradio/tree/main/js/markdown-code
  // TODO could be reworked
  import { tick } from 'svelte'
  import { standardHtmlAndSvgTags } from './html-tags'
  import './prism.css'
  import { copy, create_marked, sanitize } from './utils'

  let {
    message,
    chatbot = false,
    sanitize_html = true,
    render_markdown = true,
    line_breaks = true,
    header_links = false,
    allow_tags = false,
    theme_mode = 'system',
    kind = 'bot'
  }: {
    message: string
    chatbot?: boolean
    sanitize_html?: boolean
    render_markdown?: boolean
    line_breaks?: boolean
    header_links?: boolean
    allow_tags?: string[] | boolean
    theme_mode?: 'system' | 'light' | 'dark'
    kind?: 'bot' | 'user'
  } = $props()

  let el = $state<HTMLElement>()
  const html = $derived(message && message.trim() ? process_message(message) : '')

  const marked = create_marked({
    header_links,
    line_breaks,
  })

  function escapeTags(content: string, tagsToEscape: string[] | boolean): string {
    if (tagsToEscape === true) {
      // https://www.w3schools.com/tags/
      const tagRegex = /<\/?([a-zA-Z][a-zA-Z0-9-]*)([\s>])/g
      return content.replace(tagRegex, (match, tagName, _endChar) => {
        if (!standardHtmlAndSvgTags.includes(tagName.toLowerCase())) {
          return match.replace(/</g, '&lt;').replace(/>/g, '&gt;')
        }
        return match
      })
    }

    if (Array.isArray(tagsToEscape)) {
      const tagPattern = tagsToEscape.map((tag) => ({
        open: new RegExp(`<(${tag})(\\s+[^>]*)?>`, 'gi'),
        close: new RegExp(`</(${tag})>`, 'gi')
      }))

      let result = content

      tagPattern.forEach((pattern) => {
        result = result.replace(pattern.open, (match) =>
          match.replace(/</g, '&lt;').replace(/>/g, '&gt;')
        )
        result = result.replace(pattern.close, (match) =>
          match.replace(/</g, '&lt;').replace(/>/g, '&gt;')
        )
      })
      return result
    }
    return content
  }

  function process_message(value: string): string {
    let parsedValue = value
    if (render_markdown) {
      parsedValue = marked.parse(parsedValue) as string
    }

    if (allow_tags) {
      parsedValue = escapeTags(parsedValue, allow_tags)
    }

    if (sanitize_html) {
      parsedValue = sanitize(parsedValue)
    }
    return parsedValue
  }

  async function render_html(): Promise<void> {
    if (el) {
      const mermaidDivs = el.querySelectorAll('.mermaid')
      if (mermaidDivs.length > 0) {
        await tick()
        const { default: mermaid } = await import('mermaid')

        mermaid.initialize({
          startOnLoad: false,
          theme: theme_mode === 'dark' ? 'dark' : 'default',
          securityLevel: 'antiscript'
        })
        await mermaid.run({
          nodes: Array.from(mermaidDivs).map((node) => node as HTMLElement)
        })
      }
    }
  }

  $effect(() => {
    if (el && document.body.contains(el)) {
      render_html()
    } else {
      console.error('Element is not in the DOM')
    }
  })
</script>

<span
  {@attach copy}
  class:chatbot
  bind:this={el}
  class={['md', kind]}
  class:prose={render_markdown}
  class:dark:prose-invert={render_markdown}
>
  {@html html}
</span>

<style>
  span :global(div[class*='code_wrap']) {
    position: relative;
  }

  /* KaTeX */
  span :global(span.katex) {
    font-size: var(--text-lg);
    direction: ltr;
  }

  span :global(div[class*='code_wrap'] > button) {
    z-index: 1;
    cursor: pointer;
    border-bottom-left-radius: var(--radius-sm);
    padding: var(--spacing-md);
    width: 25px;
    height: 25px;
    position: absolute;
    right: 0;
  }

  span :global(.check) {
    opacity: 0;
    z-index: var(--layer-top);
    transition: opacity 0.2s;
    background: var(--code-background-fill);
    color: var(--body-text-color);
    position: absolute;
    top: var(--size-1-5);
    left: var(--size-1-5);
  }

  span :global(p:not(:first-child)) {
    margin-top: var(--spacing-xxl);
  }

  span :global(.md-header-anchor) {
    /* position: absolute; */
    margin-left: -25px;
    padding-right: 8px;
    line-height: 1;
    color: var(--body-text-color-subdued);
    opacity: 0;
  }

  span :global(h1:hover .md-header-anchor),
  span :global(h2:hover .md-header-anchor),
  span :global(h3:hover .md-header-anchor),
  span :global(h4:hover .md-header-anchor),
  span :global(h5:hover .md-header-anchor),
  span :global(h6:hover .md-header-anchor) {
    opacity: 1;
  }

  span.md :global(.md-header-anchor > svg) {
    color: var(--body-text-color-subdued);
  }

  span :global(table) {
    word-break: break-word;
  }

  /* link styles */
  span :global(a) {
    color: var(--color-text-link);
    text-decoration: underline;
  }

  /* table styles */
  span :global(table),
  span :global(tr),
  span :global(td),
  span :global(th) {
    border: 1px solid var(--border-color-accent);
  }

  span.chatbot :global(.bot table),
  span.chatbot :global(.bot tr),
  span.chatbot :global(.bot td),
  span.chatbot :global(.bot th) {
    border: 1px solid var(--border-color-primary);
  }

  span :global(pre) {
    overflow-x: auto;
    max-width: 100%;
  }

  /* CUSTOM */
  span :global(p) {
    font-size: 14px;
  }
  span.user :global(p) {
    font-weight: 500;
  }

  span.bot :global(h1),
  span.bot :global(h2),
  span.bot :global(h3) {
    font-size: 1.375rem;
    line-height: 1.5;
  }
  span.bot :global(h4) {
    font-size: 1.25rem;
    line-height: 1.5;
  }
  span.bot :global(h5),
  span.bot :global(h6) {
    font-size: 1.125rem;
    line-height: 1.5;
  }

  @media (min-width: 48em) {
    span.bot :global(h1),
    span.bot :global(h2),
    span.bot :global(h3),
    span.bot :global(h4) {
      font-size: 1.375rem;
    }
    span.bot :global(h5),
    span.bot :global(h6) {
      font-size: 1.25rem;
    }
  }

  span :global(pre) {
    --tw-prose-pre-code: var(--grey-200-850);
    margin-bottom: 1rem;
  }

  span :global(.copy_code_button) {
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 100% !important;
  }
</style>
