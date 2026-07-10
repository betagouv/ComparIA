import { describe, expect, it } from 'vitest'
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

const segmentText = (current: number, other: number) =>
  buildComparisonSegment(current, other, 'Autre modèle')
    .map((part) => part.text)
    .join('')

describe('buildConsumptionSummary', () => {
  it('builds the expected dense and proprietary summaries', () => {
    expect(
      consumptionSummaryToText(
        buildConsumptionSummary(
          gemma,
          claude,
          { tokens: 1458, energy_mwh: 1348 },
          { tokens: 3492, energy_mwh: 13727 }
        )
      )
    ).toBe(
      "Gemma 4 31B est un modèle de taille moyenne à l'architecture dense : il mobilise l'ensemble de ses paramètres à chaque réponse. À ce titre, il obtient la classe énergétique B.\n" +
        'Sur cette discussion, les 1 458 jetons générés représentent environ 1 348 mWh, soit près de 10 fois moins que Claude 4.6 Sonnet.'
    )

    expect(
      consumptionSummaryToText(
        buildConsumptionSummary(
          claude,
          gemma,
          { tokens: 3492, energy_mwh: 13727 },
          { tokens: 1458, energy_mwh: 1348 }
        )
      )
    ).toBe(
      "Claude 4.6 Sonnet est un modèle propriétaire de très grande taille (estimée), dont l'architecture n'est pas communiquée. Compte tenu de sa taille, il obtient la classe énergétique F.\n" +
        'Sur cette discussion, les 3 492 jetons générés représentent environ 13 727 mWh, soit près de 10 fois plus que Gemma 4 31B.'
    )
  })

  it('describes a mixture of experts with active and total parameters', () => {
    const moe = {
      ...gemma,
      name: 'Modèle MoE',
      size_class: 'XL' as const,
      arch: 'moe' as const,
      params: 671,
      active_params: 37
    }
    const summary = consumptionSummaryToText(
      buildConsumptionSummary(
        moe,
        gemma,
        { tokens: 100, energy_mwh: 100 },
        { tokens: 100, energy_mwh: 100 }
      )
    )

    expect(summary).toContain("architecture par mélange d'experts")
    expect(summary).toContain('(~37 mds sur 671)')
    expect(summary).toContain('un niveau comparable')
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

    expect(summary).toContain("modèle de très petite taille à l'architecture Matformer")
    expect(summary).toContain('elle adapte la part de ses paramètres mobilisée')
  })

  it.each([
    [1348, 1360, 'un niveau comparable à celui de Autre modèle'],
    [110, 100, '+10 % par rapport à Autre modèle'],
    [1348, 1900, '−29 % par rapport à Autre modèle'],
    [1900, 1348, '+41 % par rapport à Autre modèle'],
    [200, 100, 'près de 2 fois plus que Autre modèle'],
    [100, 200, 'près de 2 fois moins que Autre modèle']
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
    expect(result).toBe('une comparaison indisponible avec Autre modèle')
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

    expect(summary).toContain("modèle de taille moyenne, dont l'architecture")
    expect(summary).not.toContain('(estimée)')
  })
})
