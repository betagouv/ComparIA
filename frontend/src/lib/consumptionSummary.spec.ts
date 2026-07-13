import { afterEach, describe, expect, it } from 'vitest'
import { m } from '$lib/i18n/messages'
import { overwriteGetLocale } from '$lib/i18n/runtime'
import {
  buildComparisonSegment,
  buildConsumptionSummary,
  consumptionSummaryToText,
  type ConsumptionSummaryModel
} from './consumptionSummary'

const gemma: ConsumptionSummaryModel = {
  name: 'Gemma 4 31B',
  size_class: 'M',
  license: { kind: 'open-weights' },
  arch: 'dense',
  params: 31,
  active_params: null,
  energy_class: 'B'
}

const claude: ConsumptionSummaryModel = {
  name: 'Claude 4.6 Sonnet',
  size_class: 'XL',
  license: { kind: 'proprietary' },
  arch: 'na',
  params: 600,
  active_params: null,
  energy_class: 'F'
}

const plainText = (value: string) => value.replace(/<[^>]*>/g, '')
const segmentText = (current: number, other: number) =>
  plainText(buildComparisonSegment(current, other, 'Autre modèle'))

let activeLocale: 'da' | 'en' | 'fr' | 'lt' | 'sv' = 'fr'
overwriteGetLocale(() => activeLocale)
afterEach(() => (activeLocale = 'fr'))

describe('buildConsumptionSummary', () => {
  it('builds dense and proprietary summaries', () => {
    const openSummary = consumptionSummaryToText(
      buildConsumptionSummary(
        gemma,
        claude,
        { tokens: 1458, energy_mwh: 1348 },
        { tokens: 3492, energy_mwh: 13727 }
      )
    )
    const proprietarySummary = consumptionSummaryToText(
      buildConsumptionSummary(
        claude,
        gemma,
        { tokens: 3492, energy_mwh: 13727 },
        { tokens: 1458, energy_mwh: 1348 }
      )
    )

    expect(openSummary).toContain(
      'Gemma 4 31B est un modèle de taille moyenne à l’architecture dense'
    )
    expect(openSummary).toContain('1 458 jetons')
    expect(openSummary).toContain('près de 10 fois moins élevée que celle de Claude 4.6 Sonnet')
    expect(proprietarySummary).toContain(
      'Claude 4.6 Sonnet est un modèle propriétaire de très grande taille (estimée)'
    )
    expect(proprietarySummary).toContain('près de 10 fois plus élevée que celle de Gemma 4 31B')
  })

  it('describes a mixture of experts with active and total parameters', () => {
    const summary = consumptionSummaryToText(
      buildConsumptionSummary(
        {
          ...gemma,
          name: 'Modèle MoE',
          size_class: 'XL',
          arch: 'moe',
          params: 671,
          active_params: 37
        },
        gemma,
        { tokens: 100, energy_mwh: 100 },
        { tokens: 100, energy_mwh: 100 }
      )
    )

    expect(summary).toContain('architecture par mélange d’experts')
    expect(summary).toContain('environ 37 milliards sur 671 milliards')
    expect(summary).toContain('une consommation comparable')
  })

  it('handles the existing XS and Matformer repository values explicitly', () => {
    const summary = consumptionSummaryToText(
      buildConsumptionSummary(
        { ...gemma, name: 'Petit Matformer', size_class: 'XS', arch: 'matformer' },
        claude,
        { tokens: 1, energy_mwh: 1 },
        { tokens: 1, energy_mwh: 1 }
      )
    )

    expect(summary).toContain('modèle de très petite taille à l’architecture Matformer')
    expect(summary).toContain('il adapte la part de ses paramètres mobilisée')
  })

  it.each([
    [1348, 1360, 'une consommation comparable à celle de Autre modèle'],
    [110, 100, 'une consommation 10 % plus élevée que celle de Autre modèle'],
    [1348, 1900, 'une consommation 29 % moins élevée que celle de Autre modèle'],
    [1900, 1348, 'une consommation 41 % plus élevée que celle de Autre modèle'],
    [200, 100, 'une consommation près de 2 fois plus élevée que celle de Autre modèle'],
    [100, 200, 'une consommation près de 2 fois moins élevée que celle de Autre modèle']
  ])('uses the correct comparison regime for %s and %s', (current, other, expected) => {
    expect(segmentText(current as number, other as number)).toBe(expected)
  })

  it.each([
    [0, 0],
    [0, 100],
    [Number.NaN, 100],
    [Number.POSITIVE_INFINITY, 100]
  ])('does not leak an invalid ratio for %s and %s', (current, other) => {
    const result = segmentText(current, other)
    expect(result).toBe('une consommation qui ne peut pas être comparée à celle de Autre modèle')
    expect(result).not.toMatch(/NaN|Infinity/)
  })

  it('does not mark the size of a non-proprietary unknown model as estimated', () => {
    const summary = consumptionSummaryToText(
      buildConsumptionSummary(
        { ...gemma, arch: 'maybe-dense' },
        claude,
        { tokens: 1, energy_mwh: 1 },
        { tokens: 1, energy_mwh: 1 }
      )
    )

    expect(summary).toContain('modèle de taille moyenne dont l’architecture')
    expect(summary).not.toContain('(estimée)')
  })

  it.each([
    [
      'en',
      'Gemma 4 31B is a medium-sized model',
      'generating 100 tokens used approximately 100 mWh'
    ],
    ['da', 'Gemma 4 31B er en mellemstor model', 'genereringen af 100 tokens cirka 100 mWh'],
    ['sv', 'Gemma 4 31B är en mellanstor modell', 'genereringen av 100 token cirka 100 mWh'],
    ['lt', 'Gemma 4 31B yra vidutinio dydžio modelis', 'buvo sugeneruota 100 žetonų']
  ])('uses the %s translation instead of French fallback', (locale, expected, consumption) => {
    activeLocale = locale as 'da' | 'en' | 'lt' | 'sv'
    const summary = consumptionSummaryToText(
      buildConsumptionSummary(
        gemma,
        claude,
        { tokens: 100, energy_mwh: 100 },
        { tokens: 100, energy_mwh: 100 }
      )
    )

    expect(summary).toContain(expected)
    expect(summary).toContain(consumption)
    expect(summary).not.toContain('est un modèle')
  })

  it('uses grammatically correct Lithuanian wording for an estimated proprietary model', () => {
    activeLocale = 'lt'
    const summary = consumptionSummaryToText(
      buildConsumptionSummary(
        claude,
        gemma,
        { tokens: 100, energy_mwh: 100 },
        { tokens: 100, energy_mwh: 100 }
      )
    )

    expect(summary).toContain('yra nuosavybinis numatomo labai didelio dydžio modelis')
  })

  it.each([
    ['fr', 'Niveau d’ouverture'],
    ['en', 'Openness level'],
    ['da', 'Åbenhedsgrad'],
    ['sv', 'Öppenhetsgrad'],
    ['lt', 'Atvirumo lygis']
  ])('translates the openness label in %s', (locale, expected) => {
    activeLocale = locale as 'da' | 'en' | 'fr' | 'lt' | 'sv'
    expect(m['models.cards.sovereignty.title']()).toBe(expected)
    expect(m['models.opennessSovereignty.title']()).toBe(expected)
  })
})
