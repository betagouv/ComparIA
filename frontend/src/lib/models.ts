import type { APIReactionPref } from '$lib/chatService.svelte'
import { getContext, setContext } from 'svelte'
import { LICENSES, MODELS, ORGANISATIONS } from './generated'
import { m } from './i18n/messages'

export const SIZES = ['XS', 'S', 'M', 'L', 'XL'] as const
export const ARCHS = ['moe', 'dense', 'matformer', 'maybe-moe', 'maybe-dense'] as const

export type Sizes = (typeof SIZES)[number]
export type Archs = (typeof ARCHS)[number]
export type License = (typeof LICENSES)[number]
export type Organisation = (typeof ORGANISATIONS)[number]
export type Model = (typeof MODELS)[number]

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
  active_params?: number
  friendly_size: Sizes
  arch: Archs
  reasoning: boolean | 'hybrid'
  quantization?: 'q4' | 'q8'
  required_ram: number
  url?: string // FIXME required?
  // conditions: 'free' | 'copyleft' | 'restricted'
  // extra data
  elo?: number
  trust_range?: [number, number]
  total_votes?: number
  consumption_wh?: number
  'rank_p2.5'?: number
  'rank_p97.5'?: number
  prefs:
    | (Record<APIReactionPref, number> & {
        total_prefs: number
        positive_prefs_ratio: number
      })
    | null
}
export type BotModel = ReturnType<typeof parseModel>

export function parseModel(model: APIBotModel) {
  return {
    ...model,
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
          model.distribution === 'open-weights'
            ? m['models.parameters']({ number: model.params })
            : m['models.size.estimated']({ size: model.friendly_size }),
        tooltip:
          model.distribution === 'api-only' ? m['models.openWeight.tooltips.params']() : undefined
      },
      arch: {
        // FIXME need description and label for 'maybe-*'
        id: `model-arch-${model.id}`,
        variant: 'yellow' as const,
        text: m[
          `models.arch.types.${model.arch === 'maybe-moe' || model.arch === 'maybe-dense' ? 'na' : model.arch}.title`
        ](),
        tooltip:
          m[
            `models.arch.types.${model.arch === 'maybe-moe' || model.arch === 'maybe-dense' ? 'na' : model.arch}.desc`
          ]()
      },
      reasoning: model.reasoning ? ({ variant: '', text: 'Modèle de raisonnement' } as const) : null
    }
  }
}

export function setModelsContext(models: APIBotModel[]) {
  setContext(
    'models',
    models.map((model) => parseModel(model))
  )
}

export function getModelsContext() {
  return getContext<BotModel[]>('models')
}
