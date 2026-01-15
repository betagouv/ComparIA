import { ARCHS, LICENSES, MAYBE_ARCHS, MODELS, ORGANISATIONS } from '$lib/generated/models'
import { getContext, setContext } from 'svelte'
import { m } from './i18n/messages'

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

interface DatasetData {
  elo: number
  score_p2_5: number
  score_p97_5: number
  rank: number
  rank_p2_5: number
  rank_p97_5: number
  n_match: number
  mean_win_prob: number
  win_rate: number
  trust_range: [number, number]
}

interface PreferencesData {
  positive_prefs_ratio: number
  total_prefs: number
  // Positive count
  useful: number
  clear_formatting: number
  complete: number
  creative: number
  // Negative count
  incorrect: number
  instructions_not_followed: number
  superficial: number
}

export interface APIBotModel {
  new: boolean
  status: 'archived' | 'enabled'
  id: string
  simple_name: Model
  organisation: Organisation
  icon_path: string
  distribution: 'api-only' | 'open-weights' | 'fully-open-source'
  license: License
  reuse: boolean
  commercial_use: boolean | null
  release_date: string
  params: number
  active_params: number | null
  friendly_size: Sizes
  arch: AllArchs
  reasoning: boolean | 'hybrid'
  quantization: 'q4' | 'q8' | null
  required_ram: number
  url: string | null // FIXME required?
  // conditions: 'free' | 'copyleft' | 'restricted'
  wh_per_million_token: number
  data: DatasetData | null
  prefs: PreferencesData | null
}
export type APIData = { data_timestamp: number; models: APIBotModel[] }
export type Data = { lastUpdateDate: string; models: BotModel[] }
export type BotModel = ReturnType<typeof parseModel>
export type BotModelWithData = BotModel & { data: DatasetData; prefs: PreferencesData }

function isMaybeArch(arch: AllArchs): arch is MaybeArchs {
  return MAYBE_ARCHS.includes(arch as MaybeArchs)
}

export function parseModel(model: APIBotModel) {
  return {
    ...model,
    consumption_wh: Math.round(model.wh_per_million_token),
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

export function setModelsContext(data: APIData) {
  setContext('data', {
    lastUpdateDate: new Date(data.data_timestamp * 1000).toLocaleDateString(),
    models: data.models.map((model) => parseModel(model))
  })
}

export function getModelsContext() {
  return getContext<Data>('data')
}

export function getModelsWithDataContext() {
  const { models, ...data } = getContext<Data>('data')
  return {
    ...data,
    models: (
      models.filter((m) => {
        if (m.data == null) return false
        if (m.prefs == null) return false
        if (m.data.trust_range[0] > 10 || m.data.trust_range[1] > 10) return false
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
