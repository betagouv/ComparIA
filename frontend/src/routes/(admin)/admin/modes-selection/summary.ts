import type { ModeViability, ModelFilter } from '$lib/generated/admin'
import { m } from '$lib/i18n/messages'
import { cleanFilter, type ModeForm, type Pairing, type Sampling } from './mode'

/** Names to show for the ids a filter holds. */
export type Lookups = {
  llms: Map<string, string>
  labs: Map<string, string>
  licenses: Map<string, string>
}

/** One criterion of a filter in plain words, and the fields that set it. */
export type Criterion = { fields: (keyof ModelFilter)[]; text: string }

export type Warning = NonNullable<ModeViability['warnings']>[number]

const SHOWN = 3

/** A short list: the first few, then how many more. */
export function shortList(values: string[]): string {
  if (values.length <= SHOWN) return values.join(', ')
  return `${values.slice(0, SHOWN).join(', ')} +${values.length - SHOWN}`
}

function names(ids: string[] | undefined, lookup: Map<string, string>): string {
  return shortList(
    (ids ?? []).map((id) => lookup.get(id) ?? m['admin.selectionModes.unknownItem']())
  )
}

function yesNo(value: boolean, yes: string, no: string): string {
  return value ? yes : no
}

/** The criteria a filter sets, in the order the builder shows them. */
export function filterCriteria(input: ModelFilter, lookups: Lookups): Criterion[] {
  const f = cleanFilter(input)
  const out: Criterion[] = []
  const add = (fields: (keyof ModelFilter)[], text: string) => out.push({ fields, text })

  if (f.llm_ids)
    add(
      ['llm_ids'],
      m['admin.selectionModes.criteria.llms']({ names: names(f.llm_ids, lookups.llms) })
    )
  if (f.exclude_llm_ids)
    add(
      ['exclude_llm_ids'],
      m['admin.selectionModes.criteria.excludeLlms']({
        names: names(f.exclude_llm_ids, lookups.llms)
      })
    )
  if (f.lab_ids)
    add(
      ['lab_ids'],
      m['admin.selectionModes.criteria.labs']({ names: names(f.lab_ids, lookups.labs) })
    )
  if (f.exclude_lab_ids)
    add(
      ['exclude_lab_ids'],
      m['admin.selectionModes.criteria.excludeLabs']({
        names: names(f.exclude_lab_ids, lookups.labs)
      })
    )
  if (f.tags) {
    const tags = shortList(f.tags)
    add(
      ['tags', 'tags_match'],
      f.tags_match === 'all' && f.tags.length > 1
        ? m['admin.selectionModes.criteria.tagsAll']({ tags })
        : m['admin.selectionModes.criteria.tags']({ tags })
    )
  }
  if (f.exclude_tags)
    add(
      ['exclude_tags'],
      m['admin.selectionModes.criteria.excludeTags']({ tags: shortList(f.exclude_tags) })
    )
  if (f.arena_tools != null)
    add(
      ['arena_tools'],
      yesNo(
        f.arena_tools,
        m['admin.selectionModes.criteria.arenaToolsYes'](),
        m['admin.selectionModes.criteria.arenaToolsNo']()
      )
    )
  if (f.public_weights != null)
    add(
      ['public_weights'],
      yesNo(
        f.public_weights,
        m['admin.selectionModes.criteria.openWeights'](),
        m['admin.selectionModes.criteria.proprietary']()
      )
    )
  if (f.license_ids)
    add(
      ['license_ids'],
      m['admin.selectionModes.criteria.licenses']({ names: names(f.license_ids, lookups.licenses) })
    )
  if (f.eu_hostable != null)
    add(
      ['eu_hostable'],
      yesNo(
        f.eu_hostable,
        m['admin.selectionModes.criteria.euYes'](),
        m['admin.selectionModes.criteria.euNo']()
      )
    )
  if (f.size_classes)
    add(
      ['size_classes'],
      m['admin.selectionModes.criteria.sizes']({ values: f.size_classes.join(', ') })
    )
  if (f.params_min != null && f.params_max != null)
    add(
      ['params_min', 'params_max'],
      m['admin.selectionModes.criteria.paramsRange']({ min: f.params_min, max: f.params_max })
    )
  else if (f.params_min != null)
    add(['params_min'], m['admin.selectionModes.criteria.paramsMin']({ min: f.params_min }))
  else if (f.params_max != null)
    add(['params_max'], m['admin.selectionModes.criteria.paramsMax']({ max: f.params_max }))
  if (f.archs)
    add(['archs'], m['admin.selectionModes.criteria.archs']({ values: f.archs.join(', ') }))
  if (f.energy_classes)
    add(
      ['energy_classes'],
      m['admin.selectionModes.criteria.energy']({ values: f.energy_classes.join(', ') })
    )
  if (f.inputs)
    add(
      ['inputs'],
      m['admin.selectionModes.criteria.inputs']({
        values: f.inputs.map((input) => inputLabel(input)).join(', ')
      })
    )
  if (f.released_within_days != null)
    add(
      ['released_within_days'],
      m['admin.selectionModes.criteria.releasedWithin']({ days: f.released_within_days })
    )
  if (f.released_after)
    add(
      ['released_after'],
      m['admin.selectionModes.criteria.releasedAfter']({ date: f.released_after })
    )
  if (f.released_before)
    add(
      ['released_before'],
      m['admin.selectionModes.criteria.releasedBefore']({ date: f.released_before })
    )
  if (f.price_out_max != null)
    add(['price_out_max'], m['admin.selectionModes.criteria.priceOut']({ price: f.price_out_max }))
  if (f.rate_limited != null)
    add(
      ['rate_limited'],
      yesNo(
        f.rate_limited,
        m['admin.selectionModes.criteria.rateLimitedYes'](),
        m['admin.selectionModes.criteria.rateLimitedNo']()
      )
    )
  if (f.top_ranked != null)
    add(['top_ranked'], m['admin.selectionModes.criteria.topRanked']({ count: f.top_ranked }))
  return out
}

export function inputLabel(input: string): string {
  const labels: Record<string, () => string> = {
    text: m['models.cards.modalities.types.text'],
    image: m['models.cards.modalities.types.image'],
    audio: m['models.cards.modalities.types.audio'],
    video: m['models.cards.modalities.types.video']
  }
  return labels[input]?.() ?? input
}

/**
 * `toolsBlock` says the mode has pairs but is not offered: it forces tools
 * and none of them is on offer.
 */
export function warningText(warning: Warning, hasPoolB: boolean, toolsBlock = false): string {
  switch (warning) {
    case 'pool_a_empty':
      return hasPoolB
        ? m['admin.selectionModes.warnings.poolAEmpty']()
        : m['admin.selectionModes.warnings.poolEmpty']()
    case 'pool_b_empty':
      return m['admin.selectionModes.warnings.poolBEmpty']()
    case 'no_valid_pair':
      return m['admin.selectionModes.warnings.noValidPair']()
    case 'single_pair':
      return m['admin.selectionModes.warnings.singlePair']()
    case 'unknown_llm_ids':
      return m['admin.selectionModes.warnings.unknownLlms']()
    case 'unknown_tool_keys':
      return m['admin.selectionModes.warnings.unknownTools']()
    case 'tool_not_offered':
      return toolsBlock
        ? m['admin.selectionModes.warnings.forcedToolsOff']()
        : m['admin.selectionModes.warnings.toolNotOffered']()
    default:
      return warning
  }
}

export function blockedByTools(
  mode: { tools_policy?: string },
  viability: Pick<ModeViability, 'viable' | 'pairs'>
): boolean {
  return mode.tools_policy === 'forced' && !viability.viable && viability.pairs > 0
}

const PAIRING_SHORT: Record<Exclude<Pairing, 'any'>, () => string> = {
  different_lab: m['admin.selectionModes.summary.differentLab'],
  same_lab: m['admin.selectionModes.summary.sameLab'],
  different_size_class: m['admin.selectionModes.summary.differentSize'],
  same_size_class: m['admin.selectionModes.summary.sameSize']
}

const SAMPLING_SHORT: Record<Exclude<Sampling, 'uniform'>, () => string> = {
  fewer_votes: m['admin.selectionModes.summary.fewerVotes'],
  newest: m['admin.selectionModes.summary.newest']
}

type RuleInput = Partial<
  Pick<ModeForm, 'visitor_picks' | 'pairing' | 'sampling' | 'tools_policy' | 'tool_keys'>
> & {
  pool_b?: ModelFilter | null
  cohorts?: string[]
  locales?: string[]
  starts_at?: string | null
  ends_at?: string | null
}

/**
 * The rule of a mode in one line, from its row and what the draw found:
 * "Draws 2 models among 12 · no tools".
 */
export function ruleSummary(
  mode: RuleInput,
  viability: Pick<ModeViability, 'pool_a_size' | 'pool_b_size'>,
  toolLabel: (key: string) => string = (key) => key
): string {
  const split = !!mode.pool_b
  const a = viability.pool_a_size
  const b = viability.pool_b_size
  const parts: string[] = []

  const picks = mode.visitor_picks ?? 0
  const pairing = mode.pairing ?? 'any'
  const sampling = mode.sampling ?? 'uniform'
  const policy = mode.tools_policy ?? 'visitor'
  const toolKeys = mode.tool_keys ?? []

  if (picks === 0) {
    parts.push(
      split
        ? m['admin.selectionModes.summary.drawSplit']({ a, b })
        : m['admin.selectionModes.summary.draw']({ count: a })
    )
  } else if (picks === 1) {
    parts.push(
      split
        ? m['admin.selectionModes.summary.pickOneSplit']({ a, b })
        : m['admin.selectionModes.summary.pickOne']({ count: a })
    )
  } else {
    parts.push(
      split
        ? m['admin.selectionModes.summary.pickTwoSplit']({ a, b })
        : m['admin.selectionModes.summary.pickTwo']({ count: a })
    )
  }

  if (pairing !== 'any') parts.push(PAIRING_SHORT[pairing]())
  if (sampling !== 'uniform') parts.push(SAMPLING_SHORT[sampling]())

  const tools = shortList(toolKeys.map(toolLabel))
  if (policy === 'none') parts.push(m['admin.selectionModes.summary.noTools']())
  else if (policy === 'forced') parts.push(m['admin.selectionModes.summary.forcedTools']({ tools }))
  else if (toolKeys.length) parts.push(m['admin.selectionModes.summary.someTools']({ tools }))

  if (mode.cohorts?.length || mode.locales?.length || mode.starts_at || mode.ends_at)
    parts.push(m['admin.selectionModes.summary.audience']())

  return parts.join(' · ')
}
