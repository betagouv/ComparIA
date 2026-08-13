/**
 * Whole-page accessibility sweep (RGAA 4.1.2 / WCAG 2.1 AA).
 *
 * Unlike the vitest suite this runs in a real browser, so colour contrast and
 * reflow are actually checked. It needs the backend up, which is why it is not
 * part of the CI job — see README, `yarn test:a11y`.
 *
 * Automated rules catch roughly a third of real barriers. A green run means
 * nothing obvious regressed, not that a page is usable with a screen reader.
 */
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

/** Pages reachable without signing in. */
const PAGES = [
  { path: '/arene', name: 'arena — prompt' },
  { path: '/arene/modeles', name: 'model list' },
  { path: '/arene/ranking', name: 'ranking' },
  { path: '/arene/statistics', name: 'statistics' },
  { path: '/arene/settings', name: 'settings' }
]

async function analyse(page: Page) {
  return new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
}

/**
 * One accepted failure, so a new one still turns the suite red.
 *
 * app.css points --text-action-high-blue-france at the instance brand colour,
 * which lands DSFR link and button labels at 4.12:1 instead of 4.5:1. It is a
 * real RGAA 3.2 failure, left open because the fix changes the colour of every
 * action label in the product — see audits/rgaa-2026-08-13.md. Delete this once
 * the token is darkened, and delete it before publishing any conformity rate.
 */
const ACCEPTED = [{ rule: 'color-contrast', fgColor: '#6464f3' }]

function isAccepted(violation: { id: string; nodes: { any: { data?: unknown }[] }[] }) {
  return ACCEPTED.some(
    ({ rule, fgColor }) =>
      violation.id === rule &&
      violation.nodes.every((node) =>
        node.any.some((check) => (check.data as { fgColor?: string })?.fgColor === fgColor)
      )
  )
}

/** Reports the offending markup, so a failure is actionable from the log. */
function summarise(violations: Awaited<ReturnType<typeof analyse>>['violations']) {
  return violations
    .filter((v) => !isAccepted(v))
    .map(
      (v) =>
        `[${v.impact}] ${v.id} — ${v.help}\n` +
        v.nodes.map((n) => `    ${n.html.slice(0, 160)}`).join('\n')
    )
    .join('\n\n')
}

for (const { path, name } of PAGES) {
  test(`${name} has no accessibility violations`, async ({ page }) => {
    await page.goto(path)
    await page.waitForLoadState('networkidle')

    const { violations } = await analyse(page)
    expect(summarise(violations)).toBe('')
  })

  test(`${name} has no duplicate ids or dangling ARIA references`, async ({ page }) => {
    await page.goto(path)
    await page.waitForLoadState('networkidle')

    // Neither is fully covered by axe, and both were real defects here: ids
    // that only collide once a component renders twice, and aria-describedby
    // pointing at an element that renders conditionally.
    const problems = await page.evaluate(() => {
      const ids = [...document.querySelectorAll('[id]')].map((el) => el.id)
      const duplicates = [...new Set(ids.filter((id, i) => ids.indexOf(id) !== i))]

      const attrs = ['aria-labelledby', 'aria-describedby', 'aria-controls']
      const dangling = [
        ...new Set(
          [...document.querySelectorAll(attrs.map((a) => `[${a}]`).join(','))].flatMap((el) =>
            attrs.flatMap((attr) =>
              (el.getAttribute(attr) ?? '')
                .split(/\s+/)
                .filter(Boolean)
                .filter((id) => !document.getElementById(id))
                .map((id) => `<${el.tagName.toLowerCase()}> ${attr}="${id}"`)
            )
          )
        )
      ]

      return { duplicates, dangling }
    })

    expect(problems.duplicates, 'duplicate ids').toEqual([])
    expect(problems.dangling, 'ARIA references pointing at no element').toEqual([])
  })
}

test('the arena offers a skip link that reaches the main content', async ({ page }) => {
  await page.goto('/arene')

  await page.keyboard.press('Tab')
  const skip = page.locator(':focus')
  await expect(skip).toHaveAttribute('href', '#contenu')
  await expect(skip).toBeVisible()

  await expect(page.locator('main#contenu')).toBeAttached()

  // The point of the link is what comes after it: the next stop must be past
  // the whole sidebar.
  await page.keyboard.press('Enter')
  await page.keyboard.press('Tab')
  expect(await page.evaluate(() => !!document.activeElement?.closest('main'))).toBe(true)
})

test('the model list stays readable at 320px', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 })
  await page.goto('/arene/modeles')
  await page.waitForLoadState('networkidle')

  const overflows = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
  )
  expect(overflows, 'horizontal scrolling at 320px').toBe(false)
})

test('the arena has no contrast failures in dark mode', async ({ page }) => {
  await page.goto('/arene')
  await page.evaluate(() => {
    document.documentElement.setAttribute('data-fr-theme', 'dark')
    document.documentElement.setAttribute('data-fr-scheme', 'dark')
  })
  await page.waitForTimeout(300)

  const { violations } = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
  expect(summarise(violations)).toBe('')
})
