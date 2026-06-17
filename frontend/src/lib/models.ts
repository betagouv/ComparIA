import type { APILLMData, DatasetData, LLMList, PreferencesData } from '$lib/generated/backend'
import { ARCHS, LICENSES, MAYBE_ARCHS, MODELS, ORGANISATIONS } from '$lib/generated/models'
import { getContext, setContext } from 'svelte'
import { m } from './i18n/messages'
import { styleControl } from './styleControl.svelte'

export const SIZES = ['XS', 'S', 'M', 'L', 'XL'] as const
export const CONSO_SIZES = ['S', 'M', 'L'] as const

export type Sizes = (typeof SIZES)[number]
export type ConsoSizes = (typeof CONSO_SIZES)[number]
export type Archs = (typeof ARCHS)[number]
export type MaybeArchs = (typeof MAYBE_ARCHS)[number]
export type AllArchs = Archs | MaybeArchs
export type License = (typeof LICENSES)[number]
export type Organisation = (typeof ORGANISATIONS)[number]
export type Model = (typeof MODELS)[number]

export type Data = { lastUpdateDate: string | null; models: BotModel[] }
export type BotModel = ReturnType<typeof parseModel>
export type BotModelWithData = BotModel & { data: DatasetData; prefs: PreferencesData }

function isMaybeArch(arch: AllArchs): arch is MaybeArchs {
  return MAYBE_ARCHS.includes(arch as MaybeArchs)
}

export function parseModel(model: APILLMData) {
  return {
    ...model,
    consumption: Math.round(model.wh_per_million_token), // Wh/1000000 = mWh/1000
    desc: m[`generated.models.${model.simple_name}.desc`](),
    sizeDesc: m[`generated.models.${model.simple_name}.size_desc`](),
    fyi: m[`generated.models.${model.simple_name}.fyi`](),
    licenseInfos:
      model.license === 'proprietary'
        ? {
            desc: m[`generated.licenses.proprio.${model.organisation}.license_desc`](),
            reuseSpecificities:
              m[`generated.licenses.proprio.${model.organisation}.reuse_specificities`](),
            commercialUseSpecificities:
              m[`generated.licenses.proprio.${model.organisation}.commercial_use_specificities`]()
          }
        : {
            desc: m[`generated.licenses.os.${model.license}.license_desc`](),
            reuseSpecificities: m[`generated.licenses.os.${model.license}.reuse_specificities`](),
            commercialUseSpecificities:
              m[`generated.licenses.os.${model.license}.commercial_use_specificities`]()
          },
    badges: {
      license: {
        'fully-open-source': {
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
        'api-only': {
          id: `model-proprietary-${model.id}`,
          variant: 'orange' as const,
          text: m['models.licenses.type.proprietary']()
        }
      }[model.distribution],
      releaseDate: model.release_date
        ? ({
            variant: '' as const,
            text: m['models.release']({ date: model.release_date })
          } as const)
        : null,
      licenseName: {
        variant: '' as const,
        text:
          model.license === 'proprietary' ? m['models.licenses.type.proprietary']() : model.license
      },
      size: {
        id: `model-parameters-${model.id}`,
        variant: 'info' as const,
        text:
          model.distribution === 'open-weights' || model.distribution === 'fully-open-source'
            ? m['models.parameters']({ number: model.params })
            : m['models.size.estimated']({ size: model.friendly_size }),
        tooltip:
          model.distribution === 'api-only' ? m['models.openWeight.tooltips.params']() : undefined
      },
      arch: {
        id: `model-arch-${model.id}`,
        variant: 'yellow' as const,
        text: m[`generated.archs.${isMaybeArch(model.arch) ? 'na' : model.arch}.title`](),
        tooltip: m[`generated.archs.${isMaybeArch(model.arch) ? 'na' : model.arch}.desc`]()
      },
      reasoning: model.reasoning ? ({ variant: '', text: 'Modèle de raisonnement' } as const) : null
    },
    search: (['id', 'simple_name', 'organisation'] as const)
      .map((key) => model[key].toLowerCase())
      .join(' ')
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
