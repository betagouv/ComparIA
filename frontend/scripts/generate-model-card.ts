/**
 * Generate a social media visual (1080x1080 PNG) for a model card.
 *
 * This script is used for communication purposes: producing ready-to-post images
 * when a new model is added to the catalog (social media, press, etc.).
 *
 * Usage:
 *   npx tsx scripts/generate-model-card.ts <modelId> [--bg <color>] [--locale <code>]
 *   npx tsx scripts/generate-model-card.ts glm-5.1
 *   npx tsx scripts/generate-model-card.ts glm-5.1 --bg "#6A6AF4"
 *   npx tsx scripts/generate-model-card.ts glm-5.1 --locale en
 *   npx tsx scripts/generate-model-card.ts glm-5.1 --bg "#6A6AF4" --locale en
 *
 * Supported locales: da, en, fr, lt, sv (default: fr)
 * Output: static/visuals/<modelId>-<locale>.png (omits locale suffix for fr)
 *
 * Prerequisites:
 *   - playwright-core installed: npm install -D playwright-core
 *   - the frontend dev server must be running: npm run dev
 *
 * If --bg is not specified, the script reads the model's organisation from the
 * rendered page and picks a colour from the ORG_COLORS map below.
 */

import { chromium } from 'playwright-core'
import path from 'node:path'
import fs from 'node:fs'

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:5173'
const OUTPUT_DIR = path.resolve(import.meta.dirname, '..', 'static', 'visuals')
const DEFAULT_LOCALE = 'fr'
const SUPPORTED_LOCALES = ['da', 'en', 'fr', 'lt', 'sv']

// Organisation → background color mapping
// Palette derived from compar:IA UI colors and DSFR design tokens
const ORG_COLORS: Record<string, string> = {
  // French/EU ecosystem — compar:IA brand yellow
  'Mistral AI': '#FFD500',
  EuroLLM: '#FFD500',

  // US big tech — blue-france / purple tones
  OpenAI: '#6A6AF4',
  Anthropic: '#D2956A',
  Google: '#4285F4',
  Microsoft: '#00A4EF',
  xAI: '#1D1D1F',

  // Open-source / research — greens & teals
  Meta: '#0668E1',
  'Swiss AI': '#E8423F',
  Ai2: '#2FB572',
  Nous: '#58B77D',
  Nvidia: '#76B900',

  // Asian labs — warm tones
  Alibaba: '#FF6A00',
  DeepSeek: '#4D6BFE',
  Zhipu: '#4A6CF7',
  'Moonshot AI': '#6C5CE7',
  MiniMax: '#FF9575',
  '01-ai': '#ED6C02',

  // Others
  Cohere: '#39594D',
  AI21: '#9F5AE5',
  Arcee: '#FF6B6B',
  Liquid: '#00D2FF',
  jpacifico: '#A96AFE',
}

const DEFAULT_COLOR = '#6A6AF4'

function parseArgs(argv: string[]) {
  const args = argv.slice(2)
  let bg: string | undefined
  let locale: string = DEFAULT_LOCALE
  const modelIds: string[] = []

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--bg' && args[i + 1]) {
      bg = args[++i]
    } else if (args[i] === '--locale' && args[i + 1]) {
      locale = args[++i]
    } else if (!args[i].startsWith('--')) {
      modelIds.push(args[i])
    }
  }

  return { modelIds, bg, locale }
}

async function generateCard(modelId: string, locale: string, bgOverride?: string) {
  if (!SUPPORTED_LOCALES.includes(locale)) {
    console.error(`ERROR: Unsupported locale "${locale}". Supported: ${SUPPORTED_LOCALES.join(', ')}`)
    process.exit(1)
  }

  const browser = await chromium.launch({ channel: 'chrome' })
  const page = await browser.newPage({
    viewport: { width: 1080, height: 1080 },
    deviceScaleFactor: 2
  })

  const localeParam = `locale=${locale}`

  let bg = bgOverride
  if (!bg) {
    await page.goto(`${BASE_URL}/card-preview/${modelId}?${localeParam}`, { waitUntil: 'networkidle' })
    const orgText = await page
      .locator('#card-preview .fr-card__title')
      .innerText()
      .catch(() => '')
    const org = orgText.split('/')[0]?.trim()
    bg = (org && ORG_COLORS[org]) || DEFAULT_COLOR
  }

  await page.goto(
    `${BASE_URL}/card-preview/${modelId}?bg=${encodeURIComponent(bg)}&${localeParam}`,
    { waitUntil: 'networkidle' }
  )

  const card = page.locator('#card-preview')
  const visible = await card.isVisible().catch(() => false)

  if (!visible) {
    console.error(`ERROR: Model "${modelId}" not found or card did not render.`)
    await browser.close()
    process.exit(1)
  }

  fs.mkdirSync(OUTPUT_DIR, { recursive: true })

  const suffix = locale === DEFAULT_LOCALE ? '' : `-${locale}`
  const outputPath = path.join(OUTPUT_DIR, `${modelId}${suffix}.png`)
  await card.screenshot({ path: outputPath })

  console.log(`Generated: ${outputPath} (bg: ${bg}, locale: ${locale})`)
  await browser.close()
}

const { modelIds, bg, locale } = parseArgs(process.argv)
if (modelIds.length === 0) {
  console.error('Usage: npx tsx scripts/generate-model-card.ts <modelId> [--bg <color>] [--locale <code>]')
  process.exit(1)
}

for (const modelId of modelIds) {
  await generateCard(modelId, locale, bg)
}
