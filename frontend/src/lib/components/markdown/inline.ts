import { sanitize } from '$lib/utils/commons'
import { create_marked } from './utils'

const inlineMarkdown = create_marked({ header_links: false, line_breaks: false })

export function renderInlineMarkdown(value: string, allowLinks = true): string {
  return sanitize(inlineMarkdown.parseInline(value) as string, allowLinks)
}
