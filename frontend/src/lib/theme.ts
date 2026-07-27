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

/**
 * Returns a canonical CSS colour only when it is a six-digit hexadecimal value.
 * This second validation is intentional: the result is inserted in SSR CSS.
 */
export function safeHexColor(value: string | null | undefined, fallback: string): string {
  return value && HEX_COLOR.test(value) ? value.toUpperCase() : fallback
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

/**
 * Keeps a recognisable brand hue for text where possible, then moves it towards
 * the foreground extreme only as far as needed to reach AA contrast.
 */
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

export type BrandTokens = {
  primary: string
  primaryHover: string
  primaryActive: string
  primaryContrast: string
  primarySoft: string
  primarySoftest: string
  secondary: string
  secondaryText: string
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
    primarySoftest: mix(safePrimary, surfaceTarget, 0.93),
    secondary: safeSecondary,
    secondaryText: textColorWithContrast(safeSecondary, isDark ? '#161616' : '#FFFFFF')
  }
}

function cssVariables(tokens: BrandTokens): string {
  return [
    `--brand-primary:${tokens.primary}`,
    `--brand-primary-hover:${tokens.primaryHover}`,
    `--brand-primary-active:${tokens.primaryActive}`,
    `--brand-primary-contrast:${tokens.primaryContrast}`,
    `--brand-primary-soft:${tokens.primarySoft}`,
    `--brand-primary-softest:${tokens.primarySoftest}`,
    `--brand-secondary:${tokens.secondary}`,
    `--brand-secondary-text:${tokens.secondaryText}`
  ].join(';')
}

/** CSS injected in the document head during SSR, before the application hydrates. */
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

  // Repeat :root so these runtime values outrank the static fallback tokens in
  // app.css even though SvelteKit may append the stylesheet later in <head>.
  return `:root:root[data-fr-theme="light"]{${lightVariables}}:root:root[data-fr-theme="dark"]{${darkVariables}}:root:root[data-fr-theme="system"]{${lightVariables}}@media (prefers-color-scheme:dark){:root:root[data-fr-theme="system"]{${darkVariables}}}`
}

/**
 * Svelte treats a regular <style> block as static, so dynamic CSS needs a
 * head HTML node. The CSS is safe here because createBrandThemeCss admits only
 * values produced from strict six-digit hexadecimal colours.
 */
export function createBrandThemeStyle(config: BrandThemeConfig | null | undefined): string {
  return `<style id="instance-brand-theme">${createBrandThemeCss(config)}</style>`
}
