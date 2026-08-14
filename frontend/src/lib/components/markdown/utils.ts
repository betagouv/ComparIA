/* eslint-disable @typescript-eslint/no-explicit-any */
import Amuchina from 'amuchina'
import GithubSlugger from 'github-slugger'
import { type Renderer, Marked } from 'marked'
import { gfmHeadingId } from 'marked-gfm-heading-id'
import { markedHighlight } from 'marked-highlight'
import * as Prism from 'prismjs'
import sanitizeHtml from 'sanitize-html'
import 'prismjs/components/prism-bash'
import 'prismjs/components/prism-c'
import 'prismjs/components/prism-cpp'
import 'prismjs/components/prism-go'
import 'prismjs/components/prism-java'
import 'prismjs/components/prism-json'
import 'prismjs/components/prism-latex'
import 'prismjs/components/prism-markup-templating'
import 'prismjs/components/prism-php'
import 'prismjs/components/prism-python'
import 'prismjs/components/prism-rust'
import 'prismjs/components/prism-sql'
import 'prismjs/components/prism-yaml'

const LINK_ICON_CODE = `<svg class="md-link-icon" viewBox="0 0 16 16" version="1.1" width="16" height="16" aria-hidden="true" fill="currentColor"><path d="m7.775 3.275 1.25-1.25a3.5 3.5 0 1 1 4.95 4.95l-2.5 2.5a3.5 3.5 0 0 1-4.95 0 .751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018 1.998 1.998 0 0 0 2.83 0l2.5-2.5a2.002 2.002 0 0 0-2.83-2.83l-1.25 1.25a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042Zm-4.69 9.64a1.998 1.998 0 0 0 2.83 0l1.25-1.25a.751.751 0 0 1 1.042.018.751.751 0 0 1 .018 1.042l-1.25 1.25a3.5 3.5 0 1 1-4.95-4.95l2.5-2.5a3.5 3.5 0 0 1 4.95 0 .751.751 0 0 1-.018 1.042.751.751 0 0 1-1.042.018 1.998 1.998 0 0 0-2.83 0l-2.5 2.5a1.998 1.998 0 0 0 0 2.83Z"></path></svg>`

const COPY_ICON_CODE = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 15 15" color="currentColor" aria-hidden="true" aria-label="Copy" stroke-width="1.3" width="15" height="15">
  <path fill="currentColor" d="M12.728 4.545v8.182H4.545V4.545zm0 -0.909H4.545a0.909 0.909 0 0 0 -0.909 0.909v8.182a0.909 0.909 0 0 0 0.909 0.909h8.182a0.909 0.909 0 0 0 0.909 -0.909V4.545a0.909 0.909 0 0 0 -0.909 -0.909"/>
  <path fill="currentColor" d="M1.818 8.182H0.909V1.818a0.909 0.909 0 0 1 0.909 -0.909h6.364v0.909H1.818Z"/>
</svg>

`

const CHECK_ICON_CODE = `<svg xmlns="http://www.w3.org/2000/svg" width="17" height="17" viewBox="0 0 17 17" aria-hidden="true" aria-label="Copied" fill="none" stroke="currentColor" stroke-width="1.3">
  <path d="m13.813 4.781 -7.438 7.438 -3.188 -3.188"/>
</svg>
`

const COPY_BUTTON_CODE = `<button title="copy" class="copy_code_button">
  <span class="copy-text">${COPY_ICON_CODE}</span>
  <span class="check">${CHECK_ICON_CODE}</span>
</button>`

const escape_test = /[&<>"']/
const escape_replace = new RegExp(escape_test.source, 'g')
const escape_test_no_encode = /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/
const escape_replace_no_encode = new RegExp(escape_test_no_encode.source, 'g')
const escape_replacements: Record<string, any> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
}

const get_escape_replacement = (ch: string): string => escape_replacements[ch] || ''

function escape(html: string, encode?: boolean): string {
  if (encode) {
    if (escape_test.test(html)) {
      return html.replace(escape_replace, get_escape_replacement)
    }
  } else {
    if (escape_test_no_encode.test(html)) {
      return html.replace(escape_replace_no_encode, get_escape_replacement)
    }
  }

  return html
}
interface Tokenizer {
  name: string
  level: string
  start: (src: string) => number | undefined
  tokenizer: (src: string, tokens: any) => any
  renderer: (token: any) => string
}

function createBlockMathTokenizer(): Tokenizer {
  return {
    name: 'blockMath',
    level: 'block',
    start(src) {
      const i1 = src.indexOf('$$')
      const i2 = src.indexOf('\\[')
      if (i1 === -1 && i2 === -1) return undefined
      if (i1 === -1) return i2
      if (i2 === -1) return i1
      return Math.min(i1, i2)
    },
    tokenizer(src) {
      let match = /^\$\$([\s\S]+?)\$\$/.exec(src)
      if (match) return { type: 'blockMath', raw: match[0], text: match[1].trim() }
      match = /^\\\[([\s\S]+?)\\\]/.exec(src)
      if (match) return { type: 'blockMath', raw: match[0], text: match[1].trim() }
      return undefined
    },
    renderer(token) {
      return `<div class="math-block">${escape(token.text, true)}</div>\n`
    }
  }
}

function createInlineMathTokenizer(): Tokenizer {
  return {
    name: 'inlineMath',
    level: 'inline',
    start(src) {
      const i1 = src.indexOf('$')
      const i2 = src.indexOf('\\(')
      if (i1 === -1 && i2 === -1) return undefined
      if (i1 === -1) return i2
      if (i2 === -1) return i1
      return Math.min(i1, i2)
    },
    tokenizer(src) {
      if (src.startsWith('$$')) return undefined
      let match = /^\$([^$\n\s][^$\n]*?[^$\n\s]|[^$\n\s])\$/.exec(src)
      if (match) return { type: 'inlineMath', raw: match[0], text: match[1] }
      match = /^\\\(([\s\S]+?)\\\)/.exec(src)
      if (match) return { type: 'inlineMath', raw: match[0], text: match[1] }
      return undefined
    },
    renderer(token) {
      return `<span class="math-inline">${escape(token.text, true)}</span>`
    }
  }
}

function createMermaidTokenizer(): Tokenizer {
  return {
    name: 'mermaid',
    level: 'block',
    start(src) {
      return src.match(/^```mermaid\s*\n/)?.index
    },
    tokenizer(src) {
      const match = /^```mermaid\s*\n([\s\S]*?)```\s*(?:\n|$)/.exec(src)
      if (match) {
        return {
          type: 'mermaid',
          raw: match[0],
          text: match[1].trim()
        }
      }
      return undefined
    },
    renderer(token) {
      return `<div class="mermaid">${token.text}</div>\n`
    }
  }
}

const renderer: Partial<Omit<Renderer, 'constructor' | 'options'>> = {
  code(this: Renderer, { text: code, lang: infostring, escaped }) {
    const lang = (infostring ?? '').match(/\S*/)?.[0] ?? ''
    code = code.replace(/\n$/, '') + '\n'

    if (!lang || lang === 'mermaid') {
      // We include lang === "mermaid" to handle mermaid blocks that don't match our custom tokenizer
      // (i.e., those without closing ```). This handles mermaid blocks that have started streaming
      // but haven't finished yet.
      return (
        '<div class="code_wrap">' +
        COPY_BUTTON_CODE +
        '<pre><code>' +
        (escaped ? code : escape(code, true)) +
        '</code></pre></div>\n'
      )
    }
    return (
      '<div class="code_wrap">' +
      COPY_BUTTON_CODE +
      '<pre><code class="' +
      'language-' +
      escape(lang) +
      '">' +
      (escaped ? code : escape(code, true)) +
      '</code></pre></div>\n'
    )
  }
}

const slugger = new GithubSlugger()

export function create_marked({
  header_links,
  line_breaks
}: {
  header_links: boolean
  line_breaks: boolean
}): typeof marked {
  const marked = new Marked()
  marked.use(
    {
      gfm: true,
      pedantic: false,
      breaks: line_breaks
    },
    markedHighlight({
      highlight: (code: string, lang: string) => {
        if (Prism?.languages?.[lang]) {
          return Prism.highlight(code, Prism.languages[lang], lang)
        }
        return code
      }
    }),
    { renderer }
  )

  if (header_links) {
    marked.use(gfmHeadingId())
    marked.use({
      extensions: [
        {
          name: 'heading',
          level: 'block',
          renderer(token) {
            const raw = token.raw
              .toLowerCase()
              .trim()
              .replace(/<[!/a-z].*?>/gi, '')
            const id = 'h' + slugger.slug(raw)
            const level = token.depth
            const text = this.parser.parseInline(token.tokens!)

            return `<h${level} id="${id}"><a class="md-header-anchor" href="#${id}">${LINK_ICON_CODE}</a>${text}</h${level}>\n`
          }
        }
      ]
    })
  }

  marked.use({
    extensions: [createBlockMathTokenizer(), createInlineMathTokenizer(), createMermaidTokenizer()]
  })

  return marked
}

export function copy(node: HTMLElement) {
  node.addEventListener('click', handle_copy)

  async function handle_copy(event: MouseEvent): Promise<void> {
    const path = event.composedPath() as HTMLButtonElement[]

    const [copy_button] = path.filter(
      (e) => e?.tagName === 'BUTTON' && e.classList.contains('copy_code_button')
    )

    if (copy_button) {
      event.stopImmediatePropagation()

      const copy_text = copy_button.parentElement!.innerText.trim()
      const copy_button_icon = Array.from(copy_button.children)[0] as HTMLSpanElement
      const copy_sucess_button = Array.from(copy_button.children)[1] as HTMLSpanElement

      const copied = await copy_to_clipboard(copy_text)

      if (copied) copy_feedback(copy_button_icon, copy_sucess_button)

      function copy_feedback(
        _copy_button_icon: HTMLSpanElement,
        _copy_sucess_button: HTMLSpanElement
      ): void {
        _copy_button_icon.style.opacity = '0'
        _copy_sucess_button.style.opacity = '1'
        setTimeout(() => {
          _copy_button_icon.style.opacity = '1'
          _copy_sucess_button.style.opacity = '0'
        }, 2000)
      }
    }
  }

  return () => {
    node.removeEventListener('click', handle_copy)
  }
}

async function copy_to_clipboard(value: string): Promise<boolean> {
  let copied = false
  if ('clipboard' in navigator) {
    await navigator.clipboard.writeText(value)
    copied = true
  } else {
    const textArea = document.createElement('textarea')
    textArea.value = value

    textArea.style.position = 'absolute'
    textArea.style.left = '-999999px'

    document.body.prepend(textArea)
    textArea.select()

    try {
      document.execCommand('copy')
      copied = true
    } catch (error) {
      console.error(error)
      copied = false
    } finally {
      textArea.remove()
    }
  }

  return copied
}

// FIXME
// this is from https://github.com/gradio-app/gradio/blob/main/js/sanitize/browser.ts
// Rework to only use one sanitizer (other in utils/commons)

const is_external_url = (link: string | null, root = location.href): boolean => {
  try {
    return !!link && new URL(link).origin !== new URL(root).origin
  } catch (_e) {
    return false
  }
}

// Model output is untrusted, so both sanitizers below work from the same
// allow-list, built from what the renderer above actually emits. Anything that
// can load a resource, submit data or restyle the page is left out: style (both
// the element and the attribute), form, input, button-with-formaction, meta,
// link, canvas, video, audio, iframe.
const ALLOWED_TAGS = [
  'a',
  'abbr',
  'b',
  'blockquote',
  'br',
  'button',
  'caption',
  'code',
  'col',
  'colgroup',
  'dd',
  'del',
  'details',
  'div',
  'dl',
  'dt',
  'em',
  'figcaption',
  'figure',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'hr',
  'i',
  'img',
  'ins',
  'kbd',
  'li',
  'mark',
  'ol',
  'p',
  'pre',
  'q',
  's',
  'samp',
  'small',
  'span',
  'strong',
  'sub',
  'summary',
  'sup',
  'table',
  'tbody',
  'td',
  'tfoot',
  'th',
  'thead',
  'tr',
  'u',
  'ul',
  'var'
]

// Enough to draw the icons the renderer inlines, and nothing that animates or
// loads (no svg:style, svg:use, svg:image, svg:foreignObject, svg:animate).
const ALLOWED_SVG_TAGS = [
  'svg',
  'path',
  'g',
  'circle',
  'ellipse',
  'line',
  'polygon',
  'polyline',
  'rect',
  'text',
  'tspan',
  'title',
  'desc'
]

// tag -> attributes, '*' meaning every tag (sanitize-html's own shape)
const ALLOWED_ATTRIBUTES: Record<string, string[]> = {
  '*': ['class', 'id', 'title', 'lang', 'dir', 'role', 'aria-hidden', 'aria-label'],
  a: ['href', 'target', 'rel'],
  img: ['src', 'alt', 'width', 'height', 'referrerpolicy', 'loading'],
  ol: ['start'],
  details: ['open'],
  th: ['align', 'colspan', 'rowspan', 'scope'],
  td: ['align', 'colspan', 'rowspan']
}

// SVG presentation attributes, allowed in the SVG namespace only. Both spellings
// of viewBox are listed because sanitize-html lowercases attribute names.
const ALLOWED_SVG_ATTRIBUTES = [
  'viewBox',
  'viewbox',
  'version',
  'xmlns',
  'fill',
  'stroke',
  'stroke-width',
  'stroke-linecap',
  'stroke-linejoin',
  'color',
  'width',
  'height',
  'd',
  'class',
  'aria-hidden',
  'aria-label'
]

// Amuchina keys its allow-list the other way round, attribute -> tags, and
// prefixes anything outside the HTML namespace ('svg:path', 'svg:*').
function amuchinaAttributes(): Record<string, string[]> {
  const attributes: Record<string, string[]> = {}
  for (const [tag, names] of Object.entries(ALLOWED_ATTRIBUTES)) {
    for (const name of names) (attributes[name] ??= []).push(tag)
  }
  for (const name of ALLOWED_SVG_ATTRIBUTES) (attributes[name] ??= []).push('svg:*')
  return attributes
}

const amuchina = new Amuchina({
  // html/head/body are the wrappers DOMParser adds; dropping them would leave
  // nothing to read the sanitized markup back from.
  allowElements: [
    'html',
    'head',
    'body',
    ...ALLOWED_TAGS,
    ...ALLOWED_SVG_TAGS.map((tag) => `svg:${tag}`)
  ],
  allowAttributes: amuchinaAttributes()
})

// Amuchina needs a DOM, so server rendering falls back to sanitize-html with the
// same allow-list. Headings keep their generated id and code blocks their
// highlighting classes.
const SSR_OPTIONS: sanitizeHtml.IOptions = {
  allowedTags: [...ALLOWED_TAGS, ...ALLOWED_SVG_TAGS],
  allowedAttributes: {
    ...ALLOWED_ATTRIBUTES,
    svg: ALLOWED_SVG_ATTRIBUTES,
    path: ALLOWED_SVG_ATTRIBUTES,
    g: ALLOWED_SVG_ATTRIBUTES,
    circle: ALLOWED_SVG_ATTRIBUTES,
    ellipse: ALLOWED_SVG_ATTRIBUTES,
    line: ALLOWED_SVG_ATTRIBUTES,
    polygon: ALLOWED_SVG_ATTRIBUTES,
    polyline: ALLOWED_SVG_ATTRIBUTES,
    rect: ALLOWED_SVG_ATTRIBUTES,
    text: ALLOWED_SVG_ATTRIBUTES,
    tspan: ALLOWED_SVG_ATTRIBUTES
  },
  allowedSchemes: ['http', 'https', 'mailto', 'tel'],
  transformTags: {
    img: sanitizeHtml.simpleTransform('img', { referrerpolicy: 'no-referrer' })
  }
}

export function sanitize(source: string): string {
  if (typeof DOMParser === 'undefined') return sanitizeHtml(source, SSR_OPTIONS)

  const node = new DOMParser().parseFromString(source, 'text/html')
  walk_nodes(node.body, 'A', (node) => {
    if (node instanceof HTMLElement && 'target' in node) {
      if (is_external_url(node.getAttribute('href'), location.href)) {
        node.setAttribute('target', '_blank')
        node.setAttribute('rel', 'noopener noreferrer')
      }
    }
  })
  // Keeps a model-supplied image from learning which page the reader is on.
  walk_nodes(node.body, 'IMG', (node) => {
    if (node instanceof HTMLElement) node.setAttribute('referrerpolicy', 'no-referrer')
  })

  return amuchina.sanitize(node).body.innerHTML
}

function walk_nodes(
  node: Node | null | HTMLElement,
  test: string | ((node: Node | HTMLElement) => boolean),
  callback: (node: Node | HTMLElement) => void
): void {
  if (
    node &&
    ((typeof test === 'string' && node.nodeName === test) ||
      (typeof test === 'function' && test(node)))
  ) {
    callback(node)
  }
  const children = node?.childNodes || []
  for (let i = 0; i < children.length; i++) {
    walk_nodes(children[i], test, callback)
  }
}
