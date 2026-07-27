import { describe, expect, it } from 'vitest'
import {
  DEFAULT_BRAND_COLORS,
  contrastRatio,
  createBrandThemeCss,
  createBrandThemeStyle,
  createBrandTokens,
  safeHexColor
} from './theme'

describe('brand theme', () => {
  it('normalises valid hexadecimal colours and rejects CSS injection', () => {
    expect(safeHexColor('#a1b2c3', '#000000')).toBe('#A1B2C3')
    expect(safeHexColor('#fff; color:red', '#000000')).toBe('#000000')
    expect(safeHexColor('#123', '#000000')).toBe('#000000')
  })

  it('selects the most legible primary contrast colour', () => {
    const darkPrimary = createBrandTokens('#000080', '#FF9575', false)
    const lightPrimary = createBrandTokens('#F5F5F5', '#FF9575', false)

    expect(darkPrimary.primaryContrast).toBe('#FFFFFF')
    expect(lightPrimary.primaryContrast).toBe('#000000')
    expect(contrastRatio(darkPrimary.primary, darkPrimary.primaryContrast)).toBeGreaterThan(4.5)
    expect(contrastRatio(lightPrimary.primary, lightPrimary.primaryContrast)).toBeGreaterThan(4.5)
  })

  it('creates interaction and surface variants for both colour schemes', () => {
    const light = createBrandTokens('#6464F3', '#FF9575', false)
    const dark = createBrandTokens('#9898F8', '#FFCC00', true)

    expect(light.primaryHover).not.toBe(light.primary)
    expect(light.primarySoft).not.toBe(light.primary)
    expect(dark.primaryActive).not.toBe(dark.primary)
    expect(dark.primarySoftest).not.toBe(dark.primary)
    expect(contrastRatio(light.secondaryText, '#FFFFFF')).toBeGreaterThanOrEqual(4.5)
    expect(contrastRatio(dark.secondaryText, '#161616')).toBeGreaterThanOrEqual(4.5)
  })

  it('emits SSR-safe variables for light, dark, and system themes', () => {
    const css = createBrandThemeCss({
      primary_color_light: '#112233',
      primary_color_dark: '#445566',
      secondary_color_light: '#778899',
      secondary_color_dark: '#AABBCC'
    })

    expect(css).toContain(':root:root[data-fr-theme="light"]')
    expect(css).toContain(':root:root[data-fr-theme="dark"]')
    expect(css).toContain(':root:root[data-fr-theme="system"]')
    expect(css).toContain('@media (prefers-color-scheme:dark)')
    expect(css).toContain('--brand-primary:#112233')
    expect(css).not.toMatch(/undefined|null/)
  })

  it('falls back to the platform defaults for absent or unsafe values', () => {
    const css = createBrandThemeCss({ primary_color_light: '#000000}</style><script>' })

    expect(css).toContain(`--brand-primary:${DEFAULT_BRAND_COLORS.primaryLight}`)
    expect(css).not.toContain('</style>')
    expect(createBrandThemeStyle({ primary_color_light: '#000000}</style><script>' })).toContain(
      '<style id="instance-brand-theme">'
    )
  })
})
