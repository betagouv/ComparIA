import type { AgentTraceToolCall, AgentTraceToolResult } from '$lib/generated/backend'
import type { ExternalHref } from '$lib/routing'
import { isSafeWebSource } from '$lib/utils/commons'

export type ActivityStep =
  | { type: 'reasoning'; content: string }
  | { type: 'tool'; call: AgentTraceToolCall; result: AgentTraceToolResult | null }

export type WebSource = { url: ExternalHref; name: string; favicon: string | null }

export type TextSegment = { text: string; url?: ExternalHref }

export function isWebSearch(call: AgentTraceToolCall) {
  return (call.tool || call.name) === 'web_search'
}

function sourceFavicon(url: string, favicon?: string | null) {
  if (favicon && isSafeWebSource(favicon)) return favicon
  try {
    const fallback = new URL('/favicon.ico', url).href
    return isSafeWebSource(fallback) ? fallback : null
  } catch {
    return null
  }
}

const NAMED_ENTITIES: Record<string, string> = {
  amp: '&',
  apos: "'",
  gt: '>',
  lt: '<',
  nbsp: ' ',
  quot: '"'
}

/** Some search providers send page titles HTML-escaped ("d&#039;euros"). */
export function decodeEntities(text: string) {
  return text.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (entity, code: string) => {
    if (code[0] !== '#') return NAMED_ENTITIES[code.toLowerCase()] ?? entity
    const point =
      code[1].toLowerCase() === 'x' ? parseInt(code.slice(2), 16) : parseInt(code.slice(1))
    return point > 0 && point <= 0x10ffff ? String.fromCodePoint(point) : entity
  })
}

/** Sources with an http(s) address, once each, in the order they came. */
export function webSources(results: AgentTraceToolResult[]): WebSource[] {
  const sources: WebSource[] = []
  for (const source of results.flatMap((result) => result.results ?? [])) {
    const url = source.url
    if (!url || !isSafeWebSource(url) || sources.some((seen) => seen.url === url)) continue
    sources.push({
      url,
      name: source.name ? decodeEntities(source.name) : url,
      favicon: sourceFavicon(url, source.favicon)
    })
  }
  return sources
}

/** The one argument a visitor would recognise as what the model asked for. */
export function toolRequest(call: AgentTraceToolCall): string | null {
  const args = call.arguments
  if (!args) return null
  const preferredKeys = ['query', 'request', 'subject', 'name', 'title', 'url']
  const values = [
    ...preferredKeys.filter((key) => key in args).map((key) => args[key]),
    ...Object.entries(args)
      .filter(([key]) => !preferredKeys.includes(key))
      .map(([, value]) => value)
  ]
  const readable = values.find(
    (value) => ['string', 'number', 'boolean'].includes(typeof value) && String(value).trim()
  )
  return readable == null ? null : String(readable)
}

/** What a tool answered, as text, when it gave no web sources to list. */
export function toolResultText(result: AgentTraceToolResult): string | null {
  const sourceContent = (result.results ?? [])
    .map((source) => source.content || source.name)
    .filter(Boolean)
    .join('\n')
    .trim()
  if (sourceContent) return sourceContent

  const content = result.content.trim()
  if (!content || content === '{}') return null
  try {
    const parsed = JSON.parse(content)
    if (typeof parsed === 'string') return parsed
    if (parsed && typeof parsed === 'object') {
      for (const key of ['answer', 'result', 'content', 'text', 'message']) {
        if (typeof parsed[key] === 'string') return parsed[key]
      }
    }
    return null
  } catch {
    return content
  }
}

export function linkify(text: string): TextSegment[] {
  const segments: TextSegment[] = []
  const urlPattern = /https?:\/\/[^\s<>"')\]]+/gi
  let lastIndex = 0

  for (const match of text.matchAll(urlPattern)) {
    const rawUrl = match[0]
    const matchIndex = match.index ?? 0
    const trailingPunctuation = rawUrl.match(/[.,!?;:]+$/)?.[0] ?? ''
    const url = trailingPunctuation ? rawUrl.slice(0, -trailingPunctuation.length) : rawUrl

    if (matchIndex > lastIndex) segments.push({ text: text.slice(lastIndex, matchIndex) })
    if (isSafeWebSource(url)) {
      segments.push({ text: url, url })
      if (trailingPunctuation) segments.push({ text: trailingPunctuation })
    } else {
      segments.push({ text: rawUrl })
    }
    lastIndex = matchIndex + rawUrl.length
  }

  if (lastIndex < text.length) segments.push({ text: text.slice(lastIndex) })
  return segments
}
