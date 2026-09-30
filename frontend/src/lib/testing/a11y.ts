/**
 * Accessibility assertions for component tests (RGAA 4.1.2 / WCAG 2.1 AA).
 *
 * Two layers guard this codebase:
 *   - here, in jsdom, over single components. No layout and no CSS, so colour
 *     and reflow rules are off; what this catches is structure — labels, ARIA,
 *     roles, ids.
 *   - e2e/a11y.test.ts, in a real browser over whole pages, where colour
 *     contrast and reflow do run.
 *
 * Neither replaces a screen reader. Automated tooling finds roughly a third of
 * real barriers, so a clean run here means "nothing obvious broke", not
 * "accessible".
 */
import axe, { type RunOptions, type Result } from 'axe-core'
import { expect } from 'vitest'

/** Rules that need layout or a full page, neither of which jsdom provides. */
const JSDOM_UNAVAILABLE = [
  'color-contrast',
  'region',
  'landmark-one-main',
  'page-has-heading-one',
  'html-has-lang',
  'landmark-unique',
  'bypass'
]

function format(violations: Result[]): string {
  return violations
    .map((v) => {
      const where = v.nodes.map((n) => `      ${n.html.slice(0, 160)}`).join('\n')
      return `  [${v.impact}] ${v.id} — ${v.help}\n${where}\n      ${v.helpUrl}`
    })
    .join('\n\n')
}

/**
 * Fails with the offending markup inlined, so a red test says what to fix
 * without a trip to the browser.
 */
export async function expectNoA11yViolations(
  container: HTMLElement = document.body,
  options: RunOptions = {}
): Promise<void> {
  const results = await axe.run(container, {
    resultTypes: ['violations'],
    ...options,
    rules: {
      ...Object.fromEntries(JSDOM_UNAVAILABLE.map((id) => [id, { enabled: false }])),
      ...(options.rules ?? {})
    }
  })

  expect(
    results.violations,
    results.violations.length ? `\n${format(results.violations)}\n` : ''
  ).toEqual([])
}

/**
 * An id only collides once a component is on screen more than once, which is
 * exactly how the reveal screen ended up with nineteen duplicates: ids that
 * were unique inside the component, mounted once per compared model.
 */
export function expectNoDuplicateIds(container: HTMLElement = document.body): void {
  const ids = [...container.querySelectorAll('[id]')].map((el) => el.id)
  const duplicates = [...new Set(ids.filter((id, i) => ids.indexOf(id) !== i))]

  expect(duplicates, `duplicate ids: ${duplicates.join(', ')}`).toEqual([])
}

/**
 * aria-labelledby and aria-describedby pointing at an id that is not in the
 * document. The element silently loses its name or description, and axe only
 * reports the labelledby half, so this is worth checking separately.
 */
export function expectNoDanglingAriaRefs(container: HTMLElement = document.body): void {
  const attrs = ['aria-labelledby', 'aria-describedby', 'aria-controls'] as const
  const dangling = [...container.querySelectorAll(attrs.map((a) => `[${a}]`).join(','))].flatMap(
    (el) =>
      attrs.flatMap((attr) =>
        (el.getAttribute(attr) ?? '')
          .split(/\s+/)
          .filter(Boolean)
          .filter((id) => !container.ownerDocument.getElementById(id))
          .map((id) => `<${el.tagName.toLowerCase()}> ${attr}="${id}"`)
      )
  )

  expect([...new Set(dangling)], 'ARIA references pointing at no element').toEqual([])
}

/** The three structural checks, which is what most component tests want. */
export async function expectAccessible(container: HTMLElement = document.body): Promise<void> {
  expectNoDuplicateIds(container)
  expectNoDanglingAriaRefs(container)
  await expectNoA11yViolations(container)
}
