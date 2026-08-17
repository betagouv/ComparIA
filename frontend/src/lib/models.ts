import { formatCurrencyFromEuro } from '$lib/currency'
import type { APILLMData, DatasetData, LLMList, PreferencesData } from '$lib/generated/backend'
import type { Archs, EnergyClasses, MaybeArchs } from '$lib/generated/constants'
import { MAYBE_ARCHS } from '$lib/generated/constants'
import { propsToAttrs } from '$lib/utils/commons'
import { getContext, setContext } from 'svelte'
import { m } from './i18n/messages'
import { getLocale } from './i18n/runtime'
import { styleControl } from './styleControl.svelte'
import { RANK_CLASS_COUNT } from './theme'

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

export type RankClass = '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8'
type ModelRevisedRank = { rank: number; rankClass: RankClass }
export type Commons = {
  modelsCount: number
  // Only holds the classes the current fit produced, which can be fewer than
  // `MAX_RANK_CLASS`. Every read is keyed by a class that came out of the same
  // computation as the spans, so a missing key would mean the two had drifted
  // apart — see `rankClassSpans`.
  rankClasses: Record<RankClass, Record<'min' | 'max', number>>
  currency: LLMList['currency']
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
export type ModelCardSize = 'xxs' | 'xs' | 'sm' | 'md'

export function isMaybeArch(arch: Archs | MaybeArchs): arch is MaybeArchs {
  return MAYBE_ARCHS.includes(arch as MaybeArchs)
}

/** "#4 to 6", or just "#4" when the class holds a single model. */
export function rankClassLabel(span: Record<'min' | 'max', number>) {
  return span.min === span.max
    ? m['models.cards.rank.single'](span)
    : m['models.cards.rank.to'](span)
}

export function getModelCards(model: BotModel, size: ModelCardSize, commons: Commons) {
  const midProps = propsToAttrs({ class: size === 'md' ? 'text-base!' : 'text-xs!' })
  const smallProps = propsToAttrs({ class: size === 'md' ? 'text-sm!' : 'text-xxs!' })
  const contextTokens = model.context_tokens
  const archI18nKey = isMaybeArch(model.arch) ? 'na' : model.arch
  const archDescription = m[`generated.archs.${archI18nKey}.desc`]()
  const archLongName = m[`generated.archs.${archI18nKey}.long_name`]()
  // Proprietary labs do not publish parameter counts, so ours are estimates and
  // we show the size class instead of a figure we cannot source. The estimate is
  // still what the energy figures are computed from, server side.
  const estimated = model.license.kind === 'proprietary'
  return {
    size: {
      id: 'size',
      icon: 'i-ri-ruler-line',
      title: m['models.cards.size.title'](),
      badge: estimated || size === 'sm' ? undefined : model.badges.size_short,
      contentBadge: estimated ? model.badges.size : undefined,
      tooltip: m['models.cards.size.tooltip'](),
      content: estimated
        ? undefined
        : m[`models.cards.size.params_count${size === 'md' ? '' : '_short'}`]({
            count: model.params,
            midProps,
            smallProps
          }),
      subContent:
        !estimated && model.active_params
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
            count: formatCurrencyFromEuro(model.price_in, commons.currency, getLocale()),
            midProps
          }),
          subContent: m['models.cards.price.price_in']()
        },
        {
          content: m['models.cards.price.price_count']({
            count: formatCurrencyFromEuro(model.price_out, commons.currency, getLocale()),
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
      iconClass: 'text-green',
      title: m[`models.cards.energy.title${size !== 'md' ? '_short' : ''}`](),
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
      iconClass: 'text-yellow',
      title: m[`models.cards.rank.title${size !== 'md' ? '_short' : ''}`](),
      tooltip: m['models.cards.rank.tooltip'](),
      content: model.data
        ? rankClassLabel(commons.rankClasses[model.data.rankClass])
        : m['words.NA'](),
      subContent: m['models.cards.rank.detail']({ count: commons.modelsCount })
    } as const
  }
}

export function getLicenceBadge(licenseType: APILLMData['license']['kind']) {
  return {
    'open-source': {
      variant: 'green' as const,
      text: m['models.licenses.type.openSource'](),
      tooltip: m['models.openWeight.tooltips.openSource']()
    },
    'open-weights': {
      variant: 'yellow' as const,
      text: m['models.licenses.type.semiOpen'](),
      tooltip: m['models.openWeight.tooltips.openWeight']()
    },
    proprietary: {
      variant: 'orange' as const,
      text: m['models.licenses.type.proprietary']()
    }
  }[licenseType]
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
      license: { ...getLicenceBadge(licenseType), id: `llm-license-${model.id}` },
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

/**
 * Highest class number we hand out. Everything below lands in the last one.
 * The theme builds one shade per class from it, so there is a single count.
 */
export const MAX_RANK_CLASS = RANK_CLASS_COUNT

/**
 * Group models we cannot statistically tell apart.
 *
 * Walk the models from strongest to weakest. The first one opens class 1 and
 * its lower confidence bound becomes the class *anchor*. A model joins the
 * open class as long as its upper bound still reaches that anchor; otherwise
 * it opens the next class with a new anchor.
 *
 * The anchor never moves once a class is open. Letting it follow each new
 * member instead would chain small overlaps together until nearly every model
 * shared one class. Fixed, it means the same thing for every member: this
 * model is indistinguishable from the class leader.
 *
 * Past `MAX_RANK_CLASS` the classes stop splitting and the remainder shares
 * the last one, which is the single class that carries no such guarantee.
 *
 * @param models sorted by score, strongest first
 * @returns the class number of each model, in the same order
 */
export function assignRankClasses(
  models: Pick<DatasetData, 'score_p2_5' | 'score_p97_5'>[]
): number[] {
  let rankClass = 1
  let anchor = models[0]?.score_p2_5

  return models.map((model) => {
    if (model.score_p97_5 < anchor && rankClass < MAX_RANK_CLASS) {
      rankClass += 1
      anchor = model.score_p2_5
    }
    return rankClass
  })
}

/**
 * Rank span of each class, for the "1 to 11" wording on the model card and the
 * ladder in the model modal.
 *
 * Derived from whichever models are on screen rather than stored once, because
 * the class of a model follows the fit it was computed from: turning style
 * control off re-fits, re-classes, and can produce a different number of
 * classes altogether.
 */
export function rankClassSpans(models: ModelRevisedRank[]): Commons['rankClasses'] {
  const spans = {} as Commons['rankClasses']

  for (const { rank, rankClass } of models) {
    const span = spans[rankClass]
    if (!span) {
      spans[rankClass] = { min: rank, max: rank }
    } else {
      span.min = Math.min(span.min, rank)
      span.max = Math.max(span.max, rank)
    }
  }

  return spans
}

export function setModelsContext(data: LLMList) {
  const rankedModels = data.models
    .filter(({ data }) => !!data && data.trust_range[0] <= 30 && data.trust_range[1] <= 30)
    .sort((a, b) => a.data!.rank - b.data!.rank)
    .map((llm, i) => ({ id: llm.id, rank: i + 1, data: llm.data! }))

  const modelsCount = rankedModels.length
  const classes = assignRankClasses(rankedModels.map(({ data }) => data))

  const revisedRankData: Record<string, ModelRevisedRank> = Object.fromEntries(
    rankedModels.map(({ id, rank }, i) => [
      id,
      { rank, rankClass: classes[i].toString() as RankClass }
    ])
  )
  const rankClasses = rankClassSpans(Object.values(revisedRankData))

  setContext<Data>('data', {
    lastUpdateDate: data.data_timestamp
      ? new Date(data.data_timestamp * 1000).toLocaleDateString()
      : null,
    styleCoefficients: data.style_coefficients ?? {},
    models: data.models.map((model) => parseModel(model, revisedRankData[model.id!])),
    commons: {
      modelsCount,
      currency: data.currency,
      rankClasses
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
  const sorted = models
    .map((m) => {
      const active = enabled || !m.data.uncontrolled ? m.data : m.data.uncontrolled
      return { ...m, data: { ...m.data, ...active, uncontrolled: m.data.uncontrolled } }
    })
    // Sort on the active score, not on `rank`: models the plain fit dropped
    // keep their style-controlled rank, so the two numbering schemes interleave
    // and the sequence stops being monotone in score. Class assignment reads
    // the list as strongest-first and would otherwise let a class opened low
    // swallow stronger models below it.
    .sort((a, b) => b.data.elo - a.data.elo)

  // Turning style control off is a different fit of the same votes, with its
  // own confidence intervals, so the classes are recomputed from it. This is
  // the one case where a model's class legitimately moves.
  const classes = assignRankClasses(sorted.map(({ data }) => data))

  return sorted.map((m, i) => ({
    ...m,
    data: { ...m.data, rank: i + 1, rankClass: classes[i].toString() as RankClass }
  }))
}
