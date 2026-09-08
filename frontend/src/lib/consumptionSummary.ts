import { m } from '$lib/i18n/messages'
import { getLocale } from '$lib/i18n/runtime'

export const MULTIPLE_THRESHOLD = 2
export const COMPARABLE_THRESHOLD = 1.1

type SizeClass = 'XS' | 'S' | 'M' | 'L' | 'XL'
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
  usage?: string
}

export interface ConsumptionSummary {
  classification: string
  consumption: string
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>'"]/g, (character) => {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]!
  })
}

export function formatLocalizedNumber(value: number, decimals = 0): string {
  return value.toLocaleString(getLocale(), {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

function sizeDescription(model: ConsumptionSummaryModel): string {
  const size = {
    XS: () => m['reveal.impacts.summary.size.xs'](),
    S: () => m['reveal.impacts.summary.size.s'](),
    M: () => m['reveal.impacts.summary.size.m'](),
    L: () => m['reveal.impacts.summary.size.l'](),
    XL: () => m['reveal.impacts.summary.size.xl']()
  }[model.size_class]()

  if (model.license.kind !== 'proprietary') return size

  return {
    XS: () => m['reveal.impacts.summary.size.estimatedXs'](),
    S: () => m['reveal.impacts.summary.size.estimatedS'](),
    M: () => m['reveal.impacts.summary.size.estimatedM'](),
    L: () => m['reveal.impacts.summary.size.estimatedL'](),
    XL: () => m['reveal.impacts.summary.size.estimatedXl']()
  }[model.size_class]()
}

function buildClassification(model: ConsumptionSummaryModel): string {
  const inputs = {
    model: escapeHtml(model.name),
    size: sizeDescription(model),
    energyClass: model.energy_class
  }

  switch (model.arch) {
    case 'dense':
      return m['reveal.impacts.summary.classification.dense'](inputs)
    case 'moe':
      if (model.license.kind === 'proprietary') {
        return m['reveal.impacts.summary.classification.moeProprietary'](inputs)
      }
      if (model.active_params !== null) {
        return m['reveal.impacts.summary.classification.moe']({
          ...inputs,
          activeParams: formatLocalizedNumber(model.active_params),
          params: formatLocalizedNumber(model.params)
        })
      }
      return buildUnknownClassification(model, inputs)
    case 'matformer':
      return m['reveal.impacts.summary.classification.matformer'](inputs)
    case 'maybe-moe':
    case 'maybe-matformer':
    case 'maybe-dense':
    case 'na':
      return buildUnknownClassification(model, inputs)
  }
}

function buildUnknownClassification(
  model: ConsumptionSummaryModel,
  inputs: { model: string; size: string; energyClass: EnergyClass }
): string {
  return model.license.kind === 'proprietary'
    ? m['reveal.impacts.summary.classification.unknownProprietary'](inputs)
    : m['reveal.impacts.summary.classification.unknown'](inputs)
}

export function buildComparisonSegment(
  energyMwh: number,
  otherEnergyMwh: number,
  otherName: string
): string {
  const otherModel = escapeHtml(otherName)
  if (
    !Number.isFinite(energyMwh) ||
    !Number.isFinite(otherEnergyMwh) ||
    energyMwh <= 0 ||
    otherEnergyMwh <= 0
  ) {
    return m['reveal.impacts.summary.comparison.unavailable']({ otherModel })
  }

  const ratio = Math.max(energyMwh, otherEnergyMwh) / Math.min(energyMwh, otherEnergyMwh)
  const consumesMore = energyMwh > otherEnergyMwh

  if (ratio < COMPARABLE_THRESHOLD) {
    return m['reveal.impacts.summary.comparison.comparable']({ otherModel })
  }

  if (ratio >= MULTIPLE_THRESHOLD) {
    return m[
      consumesMore
        ? 'reveal.impacts.summary.comparison.multipleMore'
        : 'reveal.impacts.summary.comparison.multipleLess'
    ]({ count: formatLocalizedNumber(Math.round(ratio)), otherModel })
  }

  const percentage = consumesMore ? (ratio - 1) * 100 : (1 - 1 / ratio) * 100
  return m[
    consumesMore
      ? 'reveal.impacts.summary.comparison.percentageMore'
      : 'reveal.impacts.summary.comparison.percentageLess'
  ]({ percentage: formatLocalizedNumber(Math.round(percentage)), otherModel })
}

export function buildConsumptionSummary(
  model: ConsumptionSummaryModel,
  otherModel: ConsumptionSummaryModel,
  consumption: ConsumptionSummaryData,
  otherConsumption: ConsumptionSummaryData
): ConsumptionSummary {
  return {
    classification: buildClassification(model),
    consumption: m['reveal.impacts.summary.consumption']({
      usage: consumption.usage ?? m['reveal.impacts.usage.discussion'](),
      tokens: formatLocalizedNumber(consumption.tokens),
      energy: formatLocalizedNumber(consumption.energy_mwh),
      comparison: buildComparisonSegment(
        consumption.energy_mwh,
        otherConsumption.energy_mwh,
        otherModel.name
      )
    })
  }
}

export function consumptionSummaryToText(summary: ConsumptionSummary): string {
  return `${summary.classification}\n${summary.consumption}`.replace(/<[^>]*>/g, '')
}
