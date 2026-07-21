import { sanitize } from '$lib/utils/commons'
import { create_marked } from './utils'

const inlineMarkdown = create_marked({ header_links: false, line_breaks: false })

export function renderInlineMarkdown(value: string, allowLinks = true): string {
  const rendered = sanitize(inlineMarkdown.parseInline(value) as string)
  if (allowLinks) return rendered
  return rendered.replace(/<a(?:\s[^>]*)?>(.*?)<\/a>/gi, '$1')
}
