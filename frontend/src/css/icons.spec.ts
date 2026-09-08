/**
 * We no longer ship the whole DSFR icon sheet — see icons.css. The saving is
 * only safe while every icon we ask for is still declared, and a missing one
 * fails silently in the browser: the glyph is simply absent, no error.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = join(import.meta.dirname, '..')

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry)
    return statSync(path).isDirectory() ? walk(path) : [path]
  })
}

/** Every DSFR icon name our stylesheets can resolve. */
function declared(): Set<string> {
  const sheet = readFileSync(join(root, 'css/icons.css'), 'utf8')
  const imported = [...sheet.matchAll(/@import '([^']+)'/g)].map(([, spec]) =>
    readFileSync(join(root, '..', 'node_modules', spec), 'utf8')
  )
  return new Set(
    [sheet, ...imported].flatMap((css) =>
      [...css.matchAll(/\.fr-icon-([a-z0-9-]+)::?(?:before|after)/g)].map(([, name]) => name)
    )
  )
}

/**
 * `icon` props, which Button and Link turn into `fr-icon-${icon}`. The uno
 * icons (i-ri-, i-ai-) go through a different pipeline that tree-shakes itself.
 */
function requested(): Map<string, string> {
  const found = new Map<string, string>()
  for (const path of walk(join(root, 'routes')).concat(walk(join(root, 'lib')))) {
    if (!/\.(svelte|ts)$/.test(path) || /\.(spec|test)\.ts$/.test(path)) continue
    const source = readFileSync(path, 'utf8')
    // `icon="x"` in markup, `icon: 'x'` in the config objects that feed it.
    for (const [, name] of source.matchAll(/\bicon[=:]\s*["']([a-z0-9-]+)["']/g)) {
      if (!name.startsWith('i-')) found.set(name, path)
    }
  }
  return found
}

describe('DSFR icons', () => {
  it('declares every icon the components ask for', () => {
    const available = declared()
    const missing = [...requested()]
      .filter(([name]) => !available.has(name))
      .map(([name, path]) => `${name} (${path.slice(root.length + 1)})`)

    expect(missing, 'copy the svg into static/icons and add a rule in css/icons.css').toEqual([])
  })

  it('still trims the sheet rather than pulling the whole set back in', () => {
    // The full DSFR sheet is over a thousand icons and 1.8 MB of the bundle.
    expect(declared().size).toBeLessThan(400)
  })
})
