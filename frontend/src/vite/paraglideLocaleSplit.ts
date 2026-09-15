import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import type { Plugin } from 'vite'

// Paraglide's `locale-modules` output imports every locale file statically
// from messages/_index.js, so the client downloads all of them. In the client
// build only, this rewrites those imports into one dynamic import picked by
// getLocale(), which reads the PARAGLIDE_LOCALE cookie hooks.server.ts sets on
// every response. Rolldown then emits one chunk per locale and the browser
// fetches only the visitor's. Switching language already reloads the page, so
// the next locale is fetched then. The server bundle keeps every locale.
//
// Two more rewrites keep the chunks small:
//
// - With every locale alias bound to the same module, the per-message
//   dispatchers (`if (locale === "da") return __da.x(inputs)` ...) only add
//   weight, so their bodies collapse to a single call. One thing is lost in
//   the browser: a per-call `{ locale }` option. Nothing in this codebase
//   passes one, and honouring it would mean loading a second locale from a
//   synchronous message function.
// - Untranslated keys are `export { x } from "./fr.js"` in the locale file.
//   That static edge makes rolldown give fr.js a facade chunk on top of its
//   real one, which every French visitor would download for nothing. The
//   lines are dropped instead, and the loader for such a locale fetches its
//   own chunk and the base one in parallel and merges them, base first.

type Options = {
  // Same values as paraglideVitePlugin's `project` and `outdir`.
  project: string
  outdir: string
}

export type Settings = { locales: string[]; baseLocale: string }

const IMPORT_LINE = /^import \* as (\S+) from "\.\/(.+)\.js"$/
const RUNTIME_IMPORT = /^import \{[^}]*\bgetLocale\b[^}]*\} from "\.\.\/runtime\.js"$/m
const REEXPORT_LINE = /^export \{ \w+ \} from "\.\/(.+)\.js"$/
const LOCALE_PICK = '\tconst locale = experimentalStaticLocale ?? options.locale ?? getLocale()\n'
const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const DISPATCHER_BODY = new RegExp(
  escape(LOCALE_PICK) +
    '(?:\tif \\(locale === "[^"]+"\\) return __\\S+\\.(\\w+)\\(inputs\\)\n)+' +
    '\treturn __\\S+\\.(\\w+)\\(inputs\\)\n',
  'g'
)

function fail(message: string): never {
  throw new Error(
    `paraglideLocaleSplit: ${message}. Paraglide's locale-modules output changed shape; ` +
      'update src/vite/paraglideLocaleSplit.ts or drop it from vite.config.ts'
  )
}

// Which locale a messages/<locale>.js file re-exports untranslated keys from,
// or undefined when it is complete.
export function fallbackOf(code: string, locale: string, baseLocale: string): string | undefined {
  const targets = new Set<string>()
  for (const line of code.split('\n')) {
    const match = line.match(REEXPORT_LINE)
    if (match) targets.add(match[1])
  }
  if (targets.size === 0) return
  if (targets.size > 1 || !targets.has(baseLocale)) {
    fail(`${locale}.js falls back to [${[...targets]}], only the base locale is supported`)
  }
  return baseLocale
}

export function dropFallbackReexports(code: string): string {
  return code
    .split('\n')
    .filter((line) => !REEXPORT_LINE.test(line))
    .join('\n')
}

export function splitLocaleImports(
  code: string,
  { locales, baseLocale }: Settings,
  fallbacks: Map<string, string>
): string {
  if (!RUNTIME_IMPORT.test(code)) fail('_index.js no longer imports getLocale from ../runtime.js')

  const lines = code.split('\n')
  const start = lines.findIndex((line) => IMPORT_LINE.test(line))
  if (start === -1) fail('no `import * as __x from "./x.js"` block in _index.js')
  let end = start
  while (end < lines.length && IMPORT_LINE.test(lines[end])) end++

  const aliases = new Map<string, string>()
  for (const line of lines.slice(start, end)) {
    const [, alias, locale] = line.match(IMPORT_LINE)!
    aliases.set(locale, alias)
  }

  const imported = [...aliases.keys()].sort()
  const expected = [...locales].sort()
  if (imported.join(',') !== expected.join(',')) {
    fail(`_index.js imports [${imported}] but settings.json lists [${expected}]`)
  }
  if (!aliases.has(baseLocale)) fail(`base locale "${baseLocale}" has no import in _index.js`)

  const load = (locale: string) => `import(${JSON.stringify(`./${locale}.js`)})`
  const loaders = locales
    .map((locale) => {
      const fallback = fallbacks.get(locale)
      const loader = fallback
        ? `() => Promise.all([${load(fallback)}, ${load(locale)}]).then(([base, own]) => ({ ...base, ...own }))`
        : `() => ${load(locale)}`
      return `${JSON.stringify(locale)}: ${loader}`
    })
    .join(', ')
  const bindings = [...aliases.values()].map((alias) => `${alias} = __messages`).join(', ')

  lines.splice(
    start,
    end - start,
    `const __messages = await ({ ${loaders} }[getLocale()] ?? (() => ${load(baseLocale)}))()`,
    `const ${bindings}`
  )

  const joined = lines.join('\n')
  const dispatchers = joined.split(LOCALE_PICK).length - 1
  let collapsed = 0
  const output = joined.replace(DISPATCHER_BODY, (_match, _branch, name: string) => {
    collapsed++
    return `\treturn __messages.${name}(inputs)\n`
  })
  if (collapsed === 0 || collapsed !== dispatchers) {
    fail(`collapsed ${collapsed} of ${dispatchers} message dispatchers`)
  }
  return output
}

export function paraglideLocaleSplit({ project, outdir }: Options): Plugin {
  let settings: Settings
  let messagesDir: string

  return {
    name: 'paraglide-locale-split',
    enforce: 'post',
    apply: 'build',
    configResolved(config) {
      const raw = readFileSync(resolve(config.root, project, 'settings.json'), 'utf8')
      const { locales, baseLocale } = JSON.parse(raw) as Settings
      settings = { locales, baseLocale }
      messagesDir = resolve(config.root, outdir, 'messages')
    },
    transform(code, id, options) {
      const isClient = this.environment ? this.environment.name === 'client' : !options?.ssr
      if (!isClient) return

      if (id === resolve(messagesDir, '_index.js')) {
        const fallbacks = new Map<string, string>()
        for (const locale of settings.locales) {
          const file = readFileSync(resolve(messagesDir, `${locale}.js`), 'utf8')
          const fallback = fallbackOf(file, locale, settings.baseLocale)
          if (fallback) fallbacks.set(locale, fallback)
        }
        return { code: splitLocaleImports(code, settings, fallbacks), map: null }
      }

      const locale = settings.locales.find((locale) => id === resolve(messagesDir, `${locale}.js`))
      if (locale && fallbackOf(code, locale, settings.baseLocale)) {
        return { code: dropFallbackReexports(code), map: null }
      }
    }
  }
}
