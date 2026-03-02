import { expect, test } from '@playwright/test'

test.describe('Arena full flow on production', () => {
  test.use({
    baseURL: 'https://comparia.beta.gouv.fr'
  })

  // Allow retries — the production LLM backend can occasionally fail or be slow
  test.describe.configure({ retries: 2 })

  test('landing page → arena → chat → vote → reveal', async ({ page }) => {
    // Give the whole test up to 4 minutes (LLM streaming can be slow)
    test.setTimeout(240_000)

    // 1. Go to the landing page
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Clear any previous TOS acceptance so we go through the full flow
    await page.evaluate(() => localStorage.removeItem('comparia:tos'))
    await page.reload()
    await page.waitForLoadState('networkidle')

    // 2. The landing page should show the TOS checkbox and "Commencer à discuter" button
    const tosCheckbox = page.locator('#tos-home')
    await expect(tosCheckbox).toBeVisible({ timeout: 10_000 })

    const startButton = page.locator('#start_arena_btn')
    await expect(startButton).toBeVisible()

    // 3. Check the TOS checkbox (force: true because DSFR label overlays the native input)
    await tosCheckbox.check({ force: true })

    // 4. Click "Commencer à discuter" — navigates to /arene/?cgu_acceptees
    await startButton.click()
    await page.waitForLoadState('networkidle', { timeout: 15_000 })
    expect(page.url()).toContain('/arene')

    // 5. We should now be on the arena prompt screen (TOS modal should NOT appear)
    const promptTextarea = page.locator('#initial-prompt')
    await expect(promptTextarea).toBeVisible({ timeout: 10_000 })

    // 6. Click on a prompt suggestion card
    // Skip the first card (special "iasummit" category), use the second one
    const suggestionCards = page.locator('#guided-cards label')
    await expect(suggestionCards.first()).toBeVisible({ timeout: 5_000 })
    const cardCount = await suggestionCards.count()
    expect(cardCount).toBeGreaterThan(0)
    const cardIndex = cardCount > 1 ? 1 : 0
    await suggestionCards.nth(cardIndex).click()

    // The prompt textarea should now have content from the suggestion
    await expect(promptTextarea).not.toHaveValue('', { timeout: 5_000 })
    const promptValue = await promptTextarea.inputValue()
    expect(promptValue.length).toBeGreaterThan(5)

    // 7. Click "Envoyer" (Send) to start the discussion
    const sendButton = page.locator('#prompt-area button[type="submit"]')
    await expect(sendButton).toBeEnabled({ timeout: 5_000 })
    await sendButton.click()

    // 8. Wait for the chat screen to appear
    const chatArea = page.locator('#chat-area')
    await expect(chatArea).toBeVisible({ timeout: 30_000 })

    // Wait for bot messages — both models need to connect via Gradio WebSocket and start streaming.
    // Also check for an error state: if the backend fails, an error message appears instead.
    const botMessages = page.locator('.message-bot')
    const errorMessage = page.locator('#chat-area .text-error')
    await expect(botMessages.first().or(errorMessage)).toBeVisible({ timeout: 120_000 })

    // If an error appeared instead of bot messages, fail with a clear message
    if (await errorMessage.isVisible()) {
      const errorText = await errorMessage.innerText()
      throw new Error(`Backend returned an error instead of generating responses: ${errorText}`)
    }

    // Wait for streaming to complete — the reveal button becomes enabled
    const revealButton = page.getByRole('button', {
      name: /passer à la révélation/i
    })
    await expect(revealButton).toBeEnabled({ timeout: 120_000 })

    // Verify that both bots generated some content
    const botCount = await botMessages.count()
    expect(botCount).toBeGreaterThanOrEqual(2)
    for (let i = 0; i < 2; i++) {
      const messageText = await botMessages.nth(i).innerText()
      expect(messageText.length).toBeGreaterThan(10)
    }

    // 9. Click "Passer à la révélation des modèles"
    await revealButton.click()

    // 10. The vote area should appear
    const voteArea = page.locator('#vote-area')
    await expect(voteArea).toBeVisible({ timeout: 10_000 })

    // 11. Vote "Les deux se valent" (both are equal)
    // Click the label because the radio input is sr-only (hidden, custom styled)
    await page.locator('label[for="radio-both_equal"]').click()
    await expect(page.locator('#radio-both_equal')).toBeChecked()

    // 12. Click the reveal button again to submit the vote
    const submitRevealButton = page.getByRole('button', {
      name: /passer à la révélation/i
    })
    await expect(submitRevealButton).toBeEnabled({ timeout: 5_000 })
    await submitRevealButton.click()

    // 13. The reveal area should appear
    const revealArea = page.locator('#reveal-area')
    await expect(revealArea).toBeVisible({ timeout: 15_000 })

    // 14. Verify models are revealed with real model names (org/name format)
    const modelHeadings = revealArea.locator('h5')
    await expect(modelHeadings.first()).toBeVisible({ timeout: 5_000 })
    const headingCount = await modelHeadings.count()
    expect(headingCount).toBeGreaterThanOrEqual(2)
    for (let i = 0; i < 2; i++) {
      const headingText = await modelHeadings.nth(i).textContent()
      expect(headingText).toBeTruthy()
      // The revealed model name should contain "/" (org/model format)
      expect(headingText).toContain('/')
    }

    // Verify environmental impact data is shown (Wh units in energy cards)
    await expect(revealArea.getByText('Wh').first()).toBeVisible({ timeout: 5_000 })
  })
})
