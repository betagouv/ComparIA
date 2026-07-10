export const MULTIPLE_THRESHOLD = 2
export const COMPARABLE_THRESHOLD = 1.1

const SIZE_LEXICON = {
  XS: 'de très petite taille',
  S: 'de petite taille',
  M: 'de taille moyenne',
  L: 'de grande taille',
  XL: 'de très grande taille'
} as const

type SizeClass = keyof typeof SIZE_LEXICON
type EnergyClass = 'A' | 'B' | 'C' | 'D' | 'E' | 'F'

export interface ConsumptionSummaryModel {
  name: string
  size_class: SizeClass
  license: { kind: 'proprietary' | 'open-weights' | 'open-source' }
  arch: 'moe' | 'matformer' | 'dense' | 'maybe-moe' | 'maybe-matformer' | 'maybe-dense' | 'na'
  params: number
  active_params: number | null
  energy_class: EnergyClass
}

export interface ConsumptionSummaryData {
  tokens: number
  energy_mwh: number
}

export interface SummaryPart {
  text: string
  emphasized?: true
}

export interface ConsumptionSummary {
  classification: SummaryPart[]
  consumption: SummaryPart[]
}

const text = (value: string): SummaryPart => ({ text: value })
const emphasized = (value: string): SummaryPart => ({ text: value, emphasized: true })

export function formatFrenchNumber(value: number, decimals = 0): string {
  return value.toLocaleString('fr-FR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

function sizeDescription(model: ConsumptionSummaryModel): string {
  return `${SIZE_LEXICON[model.size_class]}${model.license.kind === 'proprietary' ? ' (estimée)' : ''}`
}

function buildClassification(model: ConsumptionSummaryModel): SummaryPart[] {
  const size = sizeDescription(model)
  const prefix = [emphasized(model.name), text(' est un modèle ')]
  const classConclusion = [
    text(' À ce titre, il obtient la classe énergétique '),
    emphasized(model.energy_class),
    text('.')
  ]

  switch (model.arch) {
    case 'dense':
      return [
        ...prefix,
        emphasized(size),
        text(" à l'architecture "),
        emphasized('dense'),
        text(" : il mobilise l'ensemble de ses paramètres à chaque réponse."),
        ...classConclusion
      ]

    case 'moe':
      if (model.active_params === null) return buildUnknownClassification(model, size)
      return [
        ...prefix,
        emphasized(size),
        text(" à l'architecture "),
        emphasized("par mélange d'experts"),
        text(" : il n'active qu'une partie de ses paramètres à chaque réponse (~"),
        emphasized(`${formatFrenchNumber(model.active_params)} mds`),
        text(' sur '),
        emphasized(formatFrenchNumber(model.params)),
        text(').'),
        ...classConclusion
      ]

    case 'matformer':
      return [
        ...prefix,
        emphasized(size),
        text(" à l'architecture "),
        emphasized('Matformer'),
        text(' : elle adapte la part de ses paramètres mobilisée à chaque réponse.'),
        ...classConclusion
      ]

    case 'maybe-moe':
    case 'maybe-matformer':
    case 'maybe-dense':
    case 'na':
      return buildUnknownClassification(model, size)
  }
}

function buildUnknownClassification(model: ConsumptionSummaryModel, size: string): SummaryPart[] {
  const proprietary = model.license.kind === 'proprietary'
  return [
    emphasized(model.name),
    text(' est un modèle '),
    emphasized(`${proprietary ? 'propriétaire ' : ''}${size}`),
    text(
      ", dont l'architecture n'est pas communiquée. Compte tenu de sa taille, il obtient la classe énergétique "
    ),
    emphasized(model.energy_class),
    text('.')
  ]
}

export function buildComparisonSegment(
  energyMwh: number,
  otherEnergyMwh: number,
  otherName: string
): SummaryPart[] {
  if (
    !Number.isFinite(energyMwh) ||
    !Number.isFinite(otherEnergyMwh) ||
    energyMwh <= 0 ||
    otherEnergyMwh <= 0
  ) {
    return [text('une comparaison indisponible avec '), emphasized(otherName)]
  }

  const ratio = Math.max(energyMwh, otherEnergyMwh) / Math.min(energyMwh, otherEnergyMwh)
  const consumesMore = energyMwh > otherEnergyMwh

  if (ratio < COMPARABLE_THRESHOLD) {
    return [
      text('un niveau '),
      emphasized('comparable'),
      text(' à celui de '),
      emphasized(otherName)
    ]
  }

  if (ratio >= MULTIPLE_THRESHOLD) {
    return [
      text('près de '),
      emphasized(
        `${formatFrenchNumber(Math.round(ratio))} fois ${consumesMore ? 'plus' : 'moins'}`
      ),
      text(' que '),
      emphasized(otherName)
    ]
  }

  const percentage = consumesMore ? (ratio - 1) * 100 : (1 - 1 / ratio) * 100
  return [
    emphasized(`${consumesMore ? '+' : '−'}${formatFrenchNumber(Math.round(percentage))} %`),
    text(' par rapport à '),
    emphasized(otherName)
  ]
}

export function buildConsumptionSummary(
  model: ConsumptionSummaryModel,
  otherModel: ConsumptionSummaryModel,
  consumption: ConsumptionSummaryData,
  otherConsumption: ConsumptionSummaryData
): ConsumptionSummary {
  return {
    classification: buildClassification(model),
    consumption: [
      text('Sur cette discussion, les '),
      emphasized(`${formatFrenchNumber(consumption.tokens)} jetons`),
      text(' générés représentent environ '),
      emphasized(`${formatFrenchNumber(consumption.energy_mwh)} mWh`),
      text(', soit '),
      ...buildComparisonSegment(
        consumption.energy_mwh,
        otherConsumption.energy_mwh,
        otherModel.name
      ),
      text('.')
    ]
  }
}

export function consumptionSummaryToText(summary: ConsumptionSummary): string {
  return [summary.classification, summary.consumption]
    .map((parts) => parts.map((part) => part.text).join(''))
    .join('\n')
}
