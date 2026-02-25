import { expect, test } from '@playwright/test'

test.describe('Models page', () => {
  test('opens model modal from URL hash', async ({ page }) => {
    // Navigate directly to a model page with hash
    // Using a known model ID from the production API
    await page.goto('/modeles#gemini-2.5-flash')
    await page.waitForLoadState('networkidle')

    // Wait for DSFR to initialize and open the modal
    await page.waitForTimeout(500)

    // The modal should be visible
    const modal = page.locator('#modal-model')
    await expect(modal).toBeVisible({ timeout: 10000 })

    // The modal should display the correct model name (check by aria-label or title)
    await expect(modal.getByRole('heading', { name: /Gemini 2.5 Flash/i })).toBeVisible()
  })

  test('does not open modal when hash does not match any model', async ({ page }) => {
    await page.goto('/modeles#invalid-model-id')

    await page.waitForLoadState('networkidle')

    // The modal should not be visible
    const modal = page.locator('#modal-model')
    await expect(modal).not.toBeVisible()
  })

  test('page loads normally without hash', async ({ page }) => {
    await page.goto('/modeles')

    await page.waitForLoadState('networkidle')

    // The modal should not be visible
    const modal = page.locator('#modal-model')
    await expect(modal).not.toBeVisible()

    // The page should have loaded correctly - look for visible content
    await expect(page.locator('main')).toBeVisible()
  })
})
