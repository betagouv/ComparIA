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
  { path: '/arene/settings', name: 'settings' },
  { path: '/arene/privacy', name: 'privacy policy' },
  { path: '/arene/terms', name: 'terms' },
  { path: '/arene/legal', name: 'legal notice' },
  { path: '/arene/accessibility', name: 'accessibility statement' },
  { path: '/arene/eco-design', name: 'eco-design statement' }
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

test('changing page moves focus and says where you landed', async ({ page }) => {
  await page.goto('/arene')
  await page.waitForLoadState('networkidle')

  await page.locator('nav[aria-label] a[href="/arene/modeles"]').first().click()
  await page.waitForURL('**/arene/modeles')

  // Without this, a client-side navigation leaves focus on the link that was
  // just clicked and announces nothing: the page silently swaps underneath.
  expect(await page.evaluate(() => document.activeElement?.id)).toBe('contenu')

  const announced = await page.locator('p[role="status"]').last().textContent()
  expect(announced?.trim()).toBeTruthy()
  expect(announced).not.toContain(' - ') // page name only, not the site suffix
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

/**
 * Text that is cut off rather than reflowed. Both of these bite the same way:
 * a container sized in pixels holds text that just got taller, so the overflow
 * is clipped and the reader never sees it.
 */
const CLIPPING = `
  (() => {
    const clipped = [];
    for (const el of document.querySelectorAll('main *')) {
      const style = getComputedStyle(el);
      if (style.overflow === 'visible' || el.scrollHeight <= el.clientHeight + 1) continue;
      // Deliberate scroll areas are fine; it is the accidental ones that hide text.
      if (style.overflowY === 'auto' || style.overflowY === 'scroll') continue;
      // Text hidden on purpose for screen readers is clipped by design.
      if (el.clientHeight <= 1 || el.clientWidth <= 1) continue;
      if (el.closest('[class*="sr-only"]')) continue;
      if (!el.textContent?.trim()) continue;
      clipped.push(el.tagName + '.' + String(el.className).slice(0, 40));
    }
    return [...new Set(clipped)];
  })()
`

test('text is not clipped at 200% zoom', async ({ page }) => {
  // 200% zoom is equivalent to halving the viewport at the same layout width.
  await page.setViewportSize({ width: 640, height: 512 })
  await page.goto('/arene')
  await page.waitForLoadState('networkidle')

  const clipped = await page.evaluate(CLIPPING)
  expect(clipped, 'containers clipping their text at 200% zoom').toEqual([])
})

test('text survives the RGAA 10.12 spacing overrides', async ({ page }) => {
  await page.goto('/arene')
  await page.waitForLoadState('networkidle')

  await page.addStyleTag({
    content: `* { line-height: 1.5 !important; letter-spacing: 0.12em !important;
               word-spacing: 0.16em !important; }
              p { margin-bottom: 2em !important; }`
  })
  await page.waitForTimeout(200)

  const clipped = await page.evaluate(CLIPPING)
  expect(clipped, 'containers clipping their text under forced spacing').toEqual([])
})

/**
 * Sends one prompt and drives the flow to the results screen. Both clipping
 * tests below need this, and it is the flow that actually reaches the two
 * containers with fixed heights — the prompt screen alone never exercises them.
 */
async function reachResults(page: Page) {
  await page.goto('/arene')
  await page.locator('#initial-prompt').fill('Explique en deux phrases pourquoi le ciel est bleu.')
  await page.locator('main button[type=submit].fr-btn--primary').click()

  // A fresh browser profile shows a consent modal before anything else works.
  // The DSFR opens it asynchronously, so give it a moment to appear rather
  // than testing visibility on the same tick as the click.
  const consentModal = page.locator('#fr-modal-welcome')
  await consentModal.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
  if (await consentModal.isVisible().catch(() => false)) {
    await page.locator('label[for="tos-modal"]').click()
    await page.locator('#fr-modal-welcome .fr-modal__footer button').click()
  }

  await page.locator('#chat-area').waitFor()
  await expect(page.locator('.message-bot')).toHaveCount(2)
  // Both answers are complete once the vote form shows up, not before.
  await page.locator('fieldset[id^=vote-select]').waitFor()

  await page.locator('button[data-choice="a_better"]').click()

  // The reveal button stays aria-disabled until the vote has registered, and
  // Playwright treats aria-disabled as not actionable.
  const reveal = page.locator('#send-area button.fr-icon-arrow-up-circle-line')
  await expect(reveal).toHaveAttribute('aria-disabled', 'false')
  await reveal.click()
  await page.locator('#reveal-area').waitFor()
}

test('conversation and results screens are not clipped at 200% zoom', async ({ page }) => {
  // The prompt screen has no fixed-height containers; the risk is in the chat
  // transcript (.grouped-responses has a fixed height) and the reveal card
  // (model title has an inline min-height), both reached only after a message.
  await page.setViewportSize({ width: 640, height: 512 })
  await reachResults(page)

  const clipped = await page.evaluate(CLIPPING)
  expect(clipped, 'containers clipping their text at 200% zoom').toEqual([])
})

test('conversation and results screens survive the RGAA 10.12 spacing overrides', async ({
  page
}) => {
  // Same containers as above, but wider text from forced spacing is what
  // usually finds a fixed pixel height first.
  await reachResults(page)

  await page.addStyleTag({
    content: `* { line-height: 1.5 !important; letter-spacing: 0.12em !important;
               word-spacing: 0.16em !important; }
              p { margin-bottom: 2em !important; }`
  })
  await page.waitForTimeout(200)

  const clipped = await page.evaluate(CLIPPING)
  expect(clipped, 'containers clipping their text under forced spacing').toEqual([])
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
