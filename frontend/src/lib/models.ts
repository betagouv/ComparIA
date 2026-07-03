import type { APILLMData, DatasetData, LLMList, PreferencesData } from '$lib/generated/backend'
import type { Archs, EnergyClasses, MaybeArchs } from '$lib/generated/constants'
import { MAYBE_ARCHS } from '$lib/generated/constants'
import { propsToAttrs } from '$lib/utils/commons'
import { getContext, setContext } from 'svelte'
import { m } from './i18n/messages'
import { getLocale } from './i18n/runtime'
import { styleControl } from './styleControl.svelte'

export const CONSO_SIZES = ['S', 'M', 'L'] as const
export type ConsoSizes = (typeof CONSO_SIZES)[number]

export const ENERGY_CLASS_COLORS: Record<EnergyClasses, string> = {
  A: '--green-emeraude-850-200',
  B: '--green-menthe-850-200',
  C: '--yellow-moutarde-850-200',
  D: '--yellow-tournesol-main-731  ',
  E: '--orange-terre-battue-main-645',
  F: '--red-marianne-main-472'
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
  title: m[`models.cards.modalities.types.${item.id}`]()
}))
export const SOVEREIGNTY_FIELDS = [
  'reuse',
  'commercial_use',
  'public_weights',
  'public_training_data',
  'public_training_code',
  'eu_hostable'
] as const

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
  data: DatasetData
  prefs: PreferencesData
}
export type ModelCardSize = 'xs' | 'sm' | 'md'

export function isMaybeArch(arch: Archs | MaybeArchs): arch is MaybeArchs {
  return MAYBE_ARCHS.includes(arch as MaybeArchs)
}

export function getModelCards(model: BotModel, size: ModelCardSize, commons: Commons) {
  const midProps = propsToAttrs({ class: size === 'md' ? 'text-base!' : 'text-sm!' })
  const smallProps = propsToAttrs({ class: size === 'md' ? 'text-sm!' : 'text-xs!' })
  const contextTokens = model.context_tokens
  const archI18nKey = isMaybeArch(model.arch) ? 'na' : model.arch
  const archDescription = m[`generated.archs.${archI18nKey}.desc`]()
  const archLongName = m[`generated.archs.${archI18nKey}.long_name`]()
  return {
    size: {
      id: 'size',
      icon: 'i-ri-ruler-line',
      title: m['models.cards.size.title'](),
      badge: size !== 'sm' ? model.badges.size_short : undefined,
      tooltip: m['models.cards.size.tooltip'](),
      content:
        size !== 'xs'
          ? m['models.cards.size.params_count']({
              count: model.params,
              midProps,
              smallProps
            })
          : undefined,
      subContent:
        model.license.kind === 'proprietary'
          ? m['models.cards.size.estimated']()
          : model.active_params
            ? m['models.cards.size.active_params_count']({ count: model.active_params })
            : undefined,
      desc: undefined
    } as const,
    arch: {
      id: 'arch',
      icon: 'i-ri-stack-line',
      title: m['models.cards.arch.title'](),
      tooltip: `${m['models.cards.arch.tooltip']()} ${archDescription}`,
      content: m[`generated.archs.${archI18nKey}.name`](),
      subContent: archLongName ? archLongName : undefined,
      desc: isMaybeArch(model.arch) ? archDescription : undefined
    } as const,
    context: {
      id: 'context',
      icon: 'i-ri-text-snippet',
      title: m['models.cards.context.title'](),
      tooltip: m['models.cards.context.tooltip'](),
      content: contextTokens
        ? m['models.cards.context.tokens_count']({
            count: Math.floor(contextTokens / 1000),
            midProps,
            smallProps
          })
        : m['words.NA'](),
      subContent: contextTokens
        ? m['models.cards.context.chars_count']({
            count: Math.floor((contextTokens * 4) / 1000)
          })
        : undefined,
      desc: contextTokens ? m['models.cards.context.desc']() : undefined
    } as const,
    price: {
      id: 'price',
      icon: 'i-ri-price-tag-3-line',
      title: m['models.cards.price.title'](),
      tooltip: m['models.cards.price.tooltip'](),
      desc: undefined,
      contents: [
        {
          content: m['models.cards.price.price_count']({
            count: model.price_in.toFixed(2),
            midProps
          }),
          subContent: m['models.cards.price.price_in']()
        },
        {
          content: m['models.cards.price.price_count']({
            count: model.price_out.toFixed(2),
            midProps
          }),
          subContent: m['models.cards.price.price_out']()
        }
      ]
    } as const,
    modalities: {
      id: 'modalities',
      icon: 'i-ri-shapes-line',
      title: m['models.cards.modalities.title'](),
      tooltip: m['models.cards.modalities.tooltip']()
    } as const,
    license: {
      id: 'license',
      icon: 'i-ri-copyright-line',
      title: m['models.cards.license.title'](),
      badge: model.badges.license
    } as const,
    release: {
      id: 'release',
      icon: 'i-ri-calendar-line',
      title: m['models.cards.release.title'](),
      badge: model.badges.release_short
    } as const,
    energy: {
      id: 'energy',
      icon: 'i-ri-leaf-line',
      iconClass: 'text-yellow',
      title: m[`models.cards.energy.title_${size}`](),
      tooltip: `${m['models.cards.energy.tooltip']()} ${m['models.cards.energy.desc']()}`,
      desc: undefined,
      content: size === 'xs' ? model.energy_class : undefined
    } as const,
    sovereignty: {
      id: 'sovereignty',
      icon: 'i-ri-government-line',
      title: m['models.cards.sovereignty.title'](),
      tooltip: m['models.cards.sovereignty.tooltip'](),
      content: `${model.sovereignty_score}/${SOVEREIGNTY_FIELDS.length}`,
      subContent: m['models.cards.sovereignty.sub']()
    } as const,
    rank: {
      id: 'rank',
      icon: 'i-ri-trophy-line',
      title: m[`models.cards.rank.title${size === 'xs' ? '_xs' : ''}`](),
      tooltip: m['models.cards.rank.tooltip'](),
      content: model.data
        ? m['models.cards.rank.to'](commons.rankingTiers[model.data.rankClass])
        : m['words.NA'](),
      subContent: m['models.cards.rank.detail']({ count: commons.modelsCount })
    } as const
  }
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
    sovereignty_score: SOVEREIGNTY_FIELDS.reduce((score, v) => {
      const obj = v === 'commercial_use' || v === 'reuse' ? model.license : model
      return obj[v] ? score + 1 : score
    }, 0),
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
        variant: 'brown' as const,
        text: m['models.release']({
          date: release_date.toLocaleString(locale, { year: 'numeric', month: 'numeric' })
        })
      } as const,
      release_short: {
        variant: '' as const,
        text: release_date.toLocaleString(locale, { year: 'numeric', month: 'numeric' })
      } as const,
      knowledge: model.knowledge_cutoff
        ? ({
            variant: 'brown' as const,
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
        text: m[licenseType === 'proprietary' ? 'models.size.estimated' : 'models.size.title']({
          size: model.size_class
        })
        // tooltip:
        //   licenseType === 'proprietary' ? m['models.openWeight.tooltips.params']() : undefined
      },
      size_short: {
        id: `model-parameters-${model.id}`,
        variant: 'info' as const,
        text: m['models.size.title']({ size: model.size_class })
      },
      arch: {
        id: `model-arch-${model.id}`,
        variant: 'yellow' as const,
        text: m['models.cards.arch.withName']({
          name: m[`generated.archs.${isMaybeArch(model.arch) ? 'na' : model.arch}.name`]()
        }),
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
