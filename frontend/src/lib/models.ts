import type { APILLMData, LLMList } from '$lib/generated/backend'
import type { Archs, EnergyClasses, MaybeArchs } from '$lib/generated/constants'
import { MAYBE_ARCHS } from '$lib/generated/constants'
import { getContext, setContext } from 'svelte'
import { m } from './i18n/messages'
import { getLocale } from './i18n/runtime'
import { styleControl } from './styleControl.svelte'

export const CONSO_SIZES = ['S', 'M', 'L'] as const
export type ConsoSizes = (typeof CONSO_SIZES)[number]

export const ENERGY_CLASS_COLORS: Record<EnergyClasses, string> = {
  A: '#00963a',
  B: '#4fb648',
  C: '#bdd732',
  D: '#ffec00',
  E: '#f9a01b',
  F: '#e30613'
}
export const MODALITIES = (
  [
    { id: 'text', icon: 'i-ri-file-text-line' },
    { id: 'image', icon: 'i-ri-image-upload-line' },
    { id: 'audio', icon: 'i-ri-volume-up-line' },
    { id: 'video', icon: 'i-ri-video-line' }
  ] as const
).map((item) => ({
  ...item,
  title: m[`models.technical.modalities.types.${item.id}`]()
}))

export type RankClass = '1' | '2' | '3' | '4' | '5'
type ModelRevisedRank = { rank: number; rankClass: RankClass }
export type Commons = {
  modelsCount: number
  rankingTiers: Record<RankClass, Record<'min' | 'max', number>>
}
export type Data = {
  lastUpdateDate: string | null
  styleCoefficients: Record<string, number>
  models: BotModel[]
  commons: Commons
}
export type BotModel = ReturnType<typeof parseModel>
export type BotModelWithData = BotModel & {
  data: Required<BotModel['data']>
  prefs: Required<BotModel['prefs']>
}

export function isMaybeArch(arch: Archs | MaybeArchs): arch is MaybeArchs {
  return MAYBE_ARCHS.includes(arch as MaybeArchs)
}

export function parseModel(model: APILLMData, revisedRankData?: ModelRevisedRank) {
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
    search: [model.human_id, model.name, model.lab.name].join(' '),
    data: revisedRankData ? { ...model.data!, ...revisedRankData } : null
  }
}

export function setModelsContext(data: LLMList) {
  const rankedModels = data.models
    .filter(({ data }) => !!data && data.trust_range[0] <= 30 && data.trust_range[1] <= 30)
    .sort((a, b) => a.data!.rank - b.data!.rank)
    .map((llm, i) => ({ id: llm.id, rank: i + 1 }))

  const modelsCount = rankedModels.length
  const groupRatios = [0.1, 0.25, 0.5, 0.75]
  const groupMax = groupRatios.map((r) => Math.ceil(r * modelsCount))
  function getGroup(rank: number): RankClass {
    for (let i = 0; i < groupMax.length; i++) {
      if (rank <= groupMax[i]) return (i + 1).toString() as RankClass
    }
    return '5'
  }
  const revisedRankData: Record<string, ModelRevisedRank> = Object.fromEntries(
    rankedModels.map(({ id, rank }) => [id, { rank, rankClass: getGroup(rank) }])
  )

  setContext<Data>('data', {
    lastUpdateDate: data.data_timestamp
      ? new Date(data.data_timestamp * 1000).toLocaleDateString()
      : null,
    styleCoefficients: data.style_coefficients ?? {},
    models: data.models.map((model) => parseModel(model, revisedRankData[model.id!])),
    commons: {
      modelsCount,
      rankingTiers: {
        '1': { min: 1, max: groupMax[0] },
        '2': { min: groupMax[0] + 1, max: groupMax[1] },
        '3': { min: groupMax[1] + 1, max: groupMax[2] },
        '4': { min: groupMax[2] + 1, max: groupMax[3] },
        '5': { min: groupMax[3] + 1, max: modelsCount }
      }
    }
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
    models: (models.filter((llm) => !!llm.data) as BotModelWithData[])
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
