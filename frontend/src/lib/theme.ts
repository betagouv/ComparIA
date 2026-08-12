export type BrandThemeConfig = {
  primary_color_light?: string | null
  primary_color_dark?: string | null
  secondary_color_light?: string | null
  secondary_color_dark?: string | null
}

type Rgb = { red: number; green: number; blue: number }

const HEX_COLOR = /^#[0-9A-F]{6}$/i

export const DEFAULT_BRAND_COLORS = {
  primaryLight: '#6464F3',
  primaryDark: '#9898F8',
  secondaryLight: '#FF9575',
  secondaryDark: '#FFCC00'
} as const

export function isHexColor(value: string | null | undefined): value is string {
  return !!value && HEX_COLOR.test(value)
}

export function safeHexColor(value: string | null | undefined, fallback: string): string {
  return isHexColor(value) ? value.toUpperCase() : fallback
}

function hexToRgb(hex: string): Rgb {
  const value = safeHexColor(hex, '#000000')
  return {
    red: Number.parseInt(value.slice(1, 3), 16),
    green: Number.parseInt(value.slice(3, 5), 16),
    blue: Number.parseInt(value.slice(5, 7), 16)
  }
}

function toHex({ red, green, blue }: Rgb): string {
  return `#${[red, green, blue]
    .map((value) =>
      Math.round(Math.min(255, Math.max(0, value)))
        .toString(16)
        .padStart(2, '0')
    )
    .join('')}`.toUpperCase()
}

function mix(color: string, target: string, amount: number): string {
  const source = hexToRgb(color)
  const destination = hexToRgb(target)
  return toHex({
    red: source.red + (destination.red - source.red) * amount,
    green: source.green + (destination.green - source.green) * amount,
    blue: source.blue + (destination.blue - source.blue) * amount
  })
}

function relativeLuminance(color: string): number {
  const { red, green, blue } = hexToRgb(color)
  const linear = [red, green, blue].map((channel) => {
    const value = channel / 255
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
}

export function contrastRatio(first: string, second: string): number {
  const [lighter, darker] = [relativeLuminance(first), relativeLuminance(second)].sort(
    (a, b) => b - a
  )
  return (lighter + 0.05) / (darker + 0.05)
}

function contrastColor(background: string): string {
  return contrastRatio(background, '#FFFFFF') >= 4.5 ? '#FFFFFF' : '#000000'
}

function textColorWithContrast(color: string, background: string): string {
  if (contrastRatio(color, background) >= 4.5) return color

  const target = relativeLuminance(background) > 0.5 ? '#000000' : '#FFFFFF'
  let low = 0
  let high = 1

  for (let index = 0; index < 16; index += 1) {
    const amount = (low + high) / 2
    const candidate = mix(color, target, amount)
    if (contrastRatio(candidate, background) >= 4.5) high = amount
    else low = amount
  }

  return mix(color, target, high)
}

/**
 * How many ranking classes the leaderboard hands out. Lives here because the
 * ramp below has to have one shade per class; `models.ts` reads it back.
 */
export const RANK_CLASS_COUNT = 8

export type BrandTokens = {
  primary: string
  primaryHover: string
  primaryActive: string
  primaryContrast: string
  primarySoft: string
  primarySoftHover: string
  primarySoftActive: string
  primarySoftest: string
  secondary: string
  secondaryText: string
  /** One background per ranking class, with the text colour that reads on it. */
  rankShades: { background: string; text: string }[]
}

export function createBrandTokens(
  primary: string,
  secondary: string,
  isDark: boolean
): BrandTokens {
  const safePrimary = safeHexColor(
    primary,
    isDark ? DEFAULT_BRAND_COLORS.primaryDark : DEFAULT_BRAND_COLORS.primaryLight
  )
  const safeSecondary = safeHexColor(
    secondary,
    isDark ? DEFAULT_BRAND_COLORS.secondaryDark : DEFAULT_BRAND_COLORS.secondaryLight
  )
  const interactionTarget = isDark ? '#FFFFFF' : '#000000'
  const surfaceTarget = isDark ? '#000000' : '#FFFFFF'

  return {
    primary: safePrimary,
    primaryHover: mix(safePrimary, interactionTarget, 0.12),
    primaryActive: mix(safePrimary, interactionTarget, 0.24),
    primaryContrast: contrastColor(safePrimary),
    primarySoft: mix(safePrimary, surfaceTarget, 0.84),
    primarySoftHover: mix(safePrimary, surfaceTarget, 0.76),
    primarySoftActive: mix(safePrimary, surfaceTarget, 0.68),
    primarySoftest: mix(safePrimary, surfaceTarget, 0.93),
    secondary: safeSecondary,
    secondaryText: textColorWithContrast(safeSecondary, isDark ? '#161616' : '#FFFFFF'),
    // The ranking classes are one scale, so they get one hue: the primary at
    // full strength for the first class, fading toward the page surface for
    // the last. Mixing in a second hue would read as categories rather than
    // as positions. `contrastColor` picks the label per step, which is what
    // lets the ramp span its whole range: black and white between them clear
    // 4.5:1 on any background, so no shade is off limits.
    rankShades: Array.from({ length: RANK_CLASS_COUNT }, (_, index) => {
      const background = mix(safePrimary, surfaceTarget, (index / (RANK_CLASS_COUNT - 1)) * 0.84)
      return { background, text: contrastColor(background) }
    })
  }
}

function cssVariables(tokens: BrandTokens): string {
  return [
    `--brand-primary:${tokens.primary}`,
    `--brand-primary-hover:${tokens.primaryHover}`,
    `--brand-primary-active:${tokens.primaryActive}`,
    `--brand-primary-contrast:${tokens.primaryContrast}`,
    `--brand-primary-soft:${tokens.primarySoft}`,
    `--brand-primary-soft-hover:${tokens.primarySoftHover}`,
    `--brand-primary-soft-active:${tokens.primarySoftActive}`,
    `--brand-primary-softest:${tokens.primarySoftest}`,
    `--brand-secondary:${tokens.secondary}`,
    `--brand-secondary-text:${tokens.secondaryText}`,
    ...tokens.rankShades.flatMap(({ background, text }, index) => [
      `--brand-rank-${index + 1}:${background}`,
      `--brand-rank-${index + 1}-text:${text}`
    ])
  ].join(';')
}

export function createBrandThemeCss(config: BrandThemeConfig | null | undefined): string {
  const light = createBrandTokens(
    safeHexColor(config?.primary_color_light, DEFAULT_BRAND_COLORS.primaryLight),
    safeHexColor(config?.secondary_color_light, DEFAULT_BRAND_COLORS.secondaryLight),
    false
  )
  const dark = createBrandTokens(
    safeHexColor(config?.primary_color_dark, DEFAULT_BRAND_COLORS.primaryDark),
    safeHexColor(config?.secondary_color_dark, DEFAULT_BRAND_COLORS.secondaryDark),
    true
  )
  const lightVariables = cssVariables(light)
  const darkVariables = cssVariables(dark)

  // Higher specificity keeps runtime values above static fallbacks.
  return `:root:root[data-fr-theme="light"]{${lightVariables}}:root:root[data-fr-theme="dark"]{${darkVariables}}:root:root[data-fr-theme="system"]{${lightVariables}}@media (prefers-color-scheme:dark){:root:root[data-fr-theme="system"]{${darkVariables}}}`
}

export function createBrandThemeStyle(config: BrandThemeConfig | null | undefined): string {
  return `<style id="instance-brand-theme">${createBrandThemeCss(config)}</style>`
}
