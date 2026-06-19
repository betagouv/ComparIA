import type { APILLMData, DatasetData, LLMList, PreferencesData } from '$lib/generated/backend'
import type { Archs, MaybeArchs } from '$lib/generated/constants'
import { MAYBE_ARCHS } from '$lib/generated/constants'
import { getContext, setContext } from 'svelte'
import { m } from './i18n/messages'
import { getLocale } from './i18n/runtime'
import { styleControl } from './styleControl.svelte'

export const CONSO_SIZES = ['S', 'M', 'L'] as const
export type ConsoSizes = (typeof CONSO_SIZES)[number]

export type Data = { lastUpdateDate: string | null; models: BotModel[] }
export type BotModel = ReturnType<typeof parseModel>
export type BotModelWithData = BotModel & { data: DatasetData; prefs: PreferencesData }

export function isMaybeArch(arch: Archs | MaybeArchs): arch is MaybeArchs {
  return MAYBE_ARCHS.includes(arch as MaybeArchs)
}

export function parseModel(model: APILLMData) {
  const locale = getLocale()
  if (model.public_training_code && model.public_training_data && model.public_weights) {
    model.license.kind = 'open-source'
  }
  const licenseType = model.license.kind
  const release_date = new Date(model.release_date)

  return {
    ...model,
    id: model.id!,
    release_date,
    // FIXME use created_at date instead?
    new: Math.floor((new Date() - release_date) / (1000 * 60 * 60 * 24)) < 60,
    consumption: Math.round(model.wh_per_million_token), // Wh/1000000 = mWh/1000
    badges: {
      license: {
        'open-source': {
          id: `model-os-${model.id}`,
          variant: 'green' as const,
          text: m['models.licenses.type.openSource'](),
          tooltip: m['models.openWeight.tooltips.openSource']()
        },
        'open-weights': {
          id: `model-ow-${model.id}`,
          variant: 'yellow' as const,
          text: m['models.licenses.type.semiOpen'](),
          tooltip: m['models.openWeight.tooltips.openWeight']()
        },
        proprietary: {
          id: `model-proprietary-${model.id}`,
          variant: 'orange' as const,
          text: m['models.licenses.type.proprietary']()
        }
      }[licenseType],
      release: {
        variant: '' as const,
        text: m['models.release']({
          date: release_date.toLocaleString(locale, {
            year: 'numeric',
            month: 'numeric'
          })
        })
      } as const,
      knowledge: model.knowledge_cutoff
        ? ({
            variant: '' as const,
            text: m['models.knowledge.badge']({
              date: new Date(model.knowledge_cutoff).toLocaleString(locale, {
                year: 'numeric',
                month: 'numeric'
              })
            }),
            tooltip: m['models.knowledge.tooltip']()
          } as const)
        : undefined,
      size: {
        id: `model-parameters-${model.id}`,
        variant: 'info' as const,
        text:
          licenseType === 'open-weights' || licenseType === 'open-source'
            ? m['models.parameters']({ number: model.params })
            : m['models.size.estimated']({ size: model.size_class }),
        tooltip:
          licenseType === 'proprietary' ? m['models.openWeight.tooltips.params']() : undefined
      },
      arch: {
        id: `model-arch-${model.id}`,
        variant: 'yellow' as const,
        text: m[`generated.archs.${isMaybeArch(model.arch) ? 'na' : model.arch}.title`](),
        tooltip: m[`generated.archs.${isMaybeArch(model.arch) ? 'na' : model.arch}.desc`]()
      }
    },
    search: [model.human_id, model.name, model.lab.name].join(' ')
  }
}

export function setModelsContext(data: LLMList) {
  setContext<Data>('data', {
    lastUpdateDate: data.data_timestamp
      ? new Date(data.data_timestamp * 1000).toLocaleDateString()
      : null,
    styleCoefficients: data.style_coefficients ?? {},
    models: data.models.map((model) => parseModel(model))
  })
}

export function getModelsContext() {
  return getContext<Data>('data')
}

export function getStyleCoefficients(): Record<string, number> {
  return getContext<Data>('data').styleCoefficients ?? {}
}

export function getModelsWithDataContext() {
  const { models, ...data } = getContext<Data>('data')
  return {
    ...data,
    models: (
      models.filter((m) => {
        if (m.data == null) return false
        if (m.prefs == null) return false
        if (m.data.trust_range[0] > 30 || m.data.trust_range[1] > 30) return false
        return true
      }) as BotModelWithData[]
    )
      .sort((a, b) => a.data.rank - b.data.rank)
      .map((m, i) => ({
        ...m,
        data: {
          ...m.data,
          rank: i + 1
        }
      }))
  }
}

/**
 * Pick the ranking view that matches the current Style Control toggle and
 * re-rank accordingly. Reads `styleControl.enabled` so callers that wrap it in a
 * `$derived` update live when the toggle flips. With the toggle on (default) the
 * style-controlled scores are kept; off swaps in each model's `uncontrolled`
 * (plain Bradley-Terry) view. Either way models are re-sorted by the active Elo
 * and ranks renumbered 1..N over the displayed set.
 */
export function applyStyleControl(models: BotModelWithData[]): BotModelWithData[] {
  const enabled = styleControl.enabled
  return models
    .map((m) => {
      const active = enabled || !m.data.uncontrolled ? m.data : m.data.uncontrolled
      return { ...m, data: { ...active, uncontrolled: m.data.uncontrolled } }
    })
    .sort((a, b) => a.data.rank - b.data.rank)
    .map((m, i) => ({ ...m, data: { ...m.data, rank: i + 1 } }))
}
