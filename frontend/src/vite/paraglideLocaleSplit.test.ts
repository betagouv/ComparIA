import { describe, expect, it } from 'vitest'
import { dropFallbackReexports, fallbackOf, splitLocaleImports } from './paraglideLocaleSplit'

const settings = { locales: ['da', 'fr', 'nb-NO'], baseLocale: 'fr' }

const index = [
  '/* eslint-disable */',
  'import { getLocale, experimentalStaticLocale } from "../runtime.js"',
  '',
  '/** @typedef {{}} HelloInputs */',
  'import * as __da from "./da.js"',
  'import * as __fr from "./fr.js"',
  'import * as __nb_no2 from "./nb-NO.js"',
  'const hello = /** @type {(inputs?: HelloInputs) => LocalizedString} */ ((inputs = {}, options = {}) => {',
  '\tconst locale = experimentalStaticLocale ?? options.locale ?? getLocale()',
  '\tif (locale === "da") return __da.hello(inputs)',
  '\tif (locale === "nb-NO") return __nb_no2.hello(inputs)',
  '\treturn __fr.hello(inputs)',
  '});',
  'export { hello as "hello" }',
  'const bye = ((inputs = {}, options = {}) => {',
  '\tconst locale = experimentalStaticLocale ?? options.locale ?? getLocale()',
  '\tif (locale === "da") return __da.bye(inputs)',
  '\tif (locale === "nb-NO") return __nb_no2.bye(inputs)',
  '\treturn __fr.bye(inputs)',
  '});',
  'export { bye }'
].join('\n')

describe('splitLocaleImports', () => {
  it('replaces the static imports with one dynamic import picked by getLocale', () => {
    const out = splitLocaleImports(index, settings, new Map())

    expect(out).not.toMatch(/^import \* as/m)
    expect(out).toContain(
      'const __messages = await ({ "da": () => import("./da.js"), "fr": () => import("./fr.js"), ' +
        '"nb-NO": () => import("./nb-NO.js") }[getLocale()] ?? (() => import("./fr.js")))()'
    )
    expect(out).toContain('const __da = __messages, __fr = __messages, __nb_no2 = __messages')
  })

  it('loads the base locale alongside a locale that falls back on it', () => {
    const out = splitLocaleImports(index, settings, new Map([['nb-NO', 'fr']]))

    expect(out).toContain(
      '"nb-NO": () => Promise.all([import("./fr.js"), import("./nb-NO.js")])' +
        '.then(([base, own]) => ({ ...base, ...own }))'
    )
    expect(out).toContain('"da": () => import("./da.js")')
  })

  it('collapses every dispatcher to one call and keeps the exports', () => {
    const out = splitLocaleImports(index, settings, new Map())

    expect(out).not.toContain('if (locale ===')
    expect(out).toContain(
      '((inputs = {}, options = {}) => {\n\treturn __messages.hello(inputs)\n});'
    )
    expect(out).toContain('\treturn __messages.bye(inputs)\n')
    expect(out).toContain('export { hello as "hello" }')
    expect(out).toContain('export { bye }')
  })

  it('throws when the import block is missing', () => {
    const noImports = index.replace(/^import \* as .*\n/gm, '')
    expect(() => splitLocaleImports(noImports, settings, new Map())).toThrow(/no `import \* as/)
  })

  it('throws when the imported locales differ from settings.json', () => {
    expect(() =>
      splitLocaleImports(index, { ...settings, locales: ['da', 'fr'] }, new Map())
    ).toThrow(/imports \[da,fr,nb-NO\] but settings.json lists \[da,fr\]/)
  })

  it('throws when a dispatcher body has an unexpected shape', () => {
    const odd = index.replace('\treturn __fr.bye(inputs)', '\treturn __fr.bye(inputs, options)')
    expect(() => splitLocaleImports(odd, settings, new Map())).toThrow(/collapsed 1 of 2/)
  })

  it('throws when getLocale is no longer imported', () => {
    const noRuntime = index.replace('getLocale, ', '')
    expect(() => splitLocaleImports(noRuntime, settings, new Map())).toThrow(/getLocale/)
  })
})

const nb = [
  "/** @typedef {import('../runtime.js').LocalizedString} LocalizedString */",
  'export { hello } from "./fr.js"',
  '',
  'export const bye = () => /** @type {LocalizedString} */ ("Ha det")'
].join('\n')

describe('fallbackOf', () => {
  it('names the base locale when a file re-exports from it', () => {
    expect(fallbackOf(nb, 'nb-NO', 'fr')).toBe('fr')
  })

  it('is undefined for a complete locale', () => {
    expect(fallbackOf('export const hello = () => "Bonjour"', 'fr', 'fr')).toBeUndefined()
  })

  it('throws on a fallback to another locale', () => {
    expect(() => fallbackOf(nb.replace('./fr.js', './da.js'), 'nb-NO', 'fr')).toThrow(
      /falls back to \[da\]/
    )
  })
})

describe('dropFallbackReexports', () => {
  it('removes only the re-export lines', () => {
    expect(dropFallbackReexports(nb)).toBe(
      [
        "/** @typedef {import('../runtime.js').LocalizedString} LocalizedString */",
        '',
        'export const bye = () => /** @type {LocalizedString} */ ("Ha det")'
      ].join('\n')
    )
  })
})
