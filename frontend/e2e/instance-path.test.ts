/**
 * Checks that nothing leaves the Instance path when the app is served under
 * one, for example PLAYWRIGHT_BASE_URL=http://localhost:8080/fr behind the
 * proxy of e2e/instance-path.Caddyfile. Skipped when the base URL has no path,
 * as in the plain run. See README, "Serving under a path".
 */
import { expect, test } from '@playwright/test'

test.describe('Instance path', () => {
  test.beforeEach(({ baseURL }) => {
    test.skip(!baseURL || new URL(baseURL).pathname === '/', 'the base URL has no path')
  })

  test('requests, redirects and cookies stay under the path', async ({
    page,
    context,
    baseURL
  }) => {
    const { origin, pathname } = new URL(baseURL!)
    const prefix = pathname.replace(/\/$/, '')
    const outside: string[] = []

    page.on('response', (response) => {
      const url = new URL(response.url())
      if (url.origin !== origin) return
      // Without MATOMO_URL the tracker script is asked of the origin root,
      // whatever the path: a dead request that is not the app's.
      if (url.pathname === '/matomo.js') return
      if (url.pathname !== prefix && !url.pathname.startsWith(`${prefix}/`)) {
        outside.push(`${response.status()} ${url.pathname}`)
      } else if (response.status() >= 400 && !url.pathname.startsWith(`${prefix}/api/`)) {
        // Pages and assets must be found; an API answer may be a 404 of its own,
        // such as a legal document the instance has not written.
        outside.push(`${response.status()} ${url.pathname} (error under the path)`)
      }
    })

    // The prefix alone is redirected to its slash: that redirect keeps the path.
    const bare = await page.goto(prefix)
    expect(new URL(page.url()).pathname).toBe(`${prefix}/`)
    expect(bare?.status()).toBe(200)

    await page.goto('./models')
    await page.waitForLoadState('networkidle')
    expect(new URL(page.url()).pathname).toBe(`${prefix}/models`)

    // No leftover of the placeholder the image is built with.
    for (const url of [`${prefix}/`, `${prefix}/models`]) {
      const html = await (await page.request.get(origin + url)).text()
      expect(html).not.toContain('__INSTANCE_PATH__')
    }

    expect(outside).toEqual([])

    const cookies = await context.cookies()
    expect(cookies.length).toBeGreaterThan(0)
    expect(cookies.filter((cookie) => cookie.path !== prefix)).toEqual([])
  })
})
