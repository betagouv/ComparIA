import type { ApiError } from '$lib/fastapi-client'
import type { ActivityConversation, ActivityTurn } from '$lib/generated/admin'
import { m } from '$lib/i18n/messages'

/** Filters every tab reads, carried from one tab to the next. */
export const SHARED_FILTERS = [
  'period',
  'start',
  'end',
  'mode',
  'llm_id',
  'cohort',
  'include_archived'
] as const

/** Filters only the conversation list reads. */
export const CONVERSATION_FILTERS = [
  'choice',
  'has_vote',
  'has_comment',
  'revealed',
  'category',
  'flag',
  'search'
] as const

export const PERIODS = ['24h', '7d', '30d', '90d', '365d', 'all'] as const
export const MODES = ['random', 'big-vs-small', 'small-models', 'custom'] as const
export const CHOICES = ['a_better', 'b_better', 'both_good', 'both_bad', 'idk'] as const
export const FLAGS = ['pii', 'spam', 'error', 'archived', 'not_analyzed'] as const

export function pick(params: URLSearchParams, keys: readonly string[]): URLSearchParams {
  const picked = new URLSearchParams()
  for (const key of keys) {
    const value = params.get(key)
    if (value) picked.set(key, value)
  }
  return picked
}

export function withQuery(path: string, params: URLSearchParams): string {
  const query = params.toString()
  return query ? `${path}?${query}` : path
}

/**
 * The current query with `changes` applied, as "?..." or "". The cursor is
 * always dropped first: it only means something for the filters it was
 * handed out with, so only the "next" button sets it again.
 */
export function nextQuery(params: URLSearchParams, changes: Record<string, string | null>): string {
  const next = new URLSearchParams(params)
  next.delete('cursor')
  for (const [key, value] of Object.entries(changes)) {
    if (value) next.set(key, value)
    else next.delete(key)
  }
  const query = next.toString()
  return query ? `?${query}` : ''
}

export function errorMessage(error: unknown): string {
  return (error as ApiError).detail === 'activity_query_timeout'
    ? m['admin.activity.errors.timeout']()
    : m['admin.activity.errors.generic']()
}

export function label(group: string, key: string): string {
  const message = (m as unknown as Record<string, (() => string) | undefined>)[
    `admin.activity.${group}.${key}`
  ]
  return message ? message() : key
}

/**
 * Validated together (light and dark, colour-blind checks): A and B are two
 * distinct hues, the two verdicts on both answers carry their meaning, and
 * "don't know" stays neutral.
 */
export const CHOICE_COLORS: Record<string, string> = {
  a_better: 'var(--blue-cumulus-main-526)',
  b_better: 'var(--purple-glycine-main-494)',
  both_good: 'var(--green-emeraude-main-632)',
  both_bad: 'var(--red-marianne-main-472)',
  idk: 'var(--grey-625-425)'
}

export type Side = 'a' | 'b'
export type SideVerdict = 'preferred' | 'rejected' | 'mixed' | null

/** How one answer fared over every vote of a conversation. */
export function sideVerdict(choices: (string | null)[], side: Side): SideVerdict {
  const other = side === 'a' ? 'b' : 'a'
  const wins = choices.filter((c) => c === `${side}_better` || c === 'both_good').length
  const losses = choices.filter((c) => c === `${other}_better` || c === 'both_bad').length
  if (!wins && !losses) return null
  if (wins && !losses) return 'preferred'
  if (losses && !wins) return 'rejected'
  return 'mixed'
}

/**
 * How far a conversation went: no vote, voted, voted and revealed the models.
 * The funnel on the overview counts the same steps.
 */
export const STAGES = ['started', 'voted', 'revealed'] as const
export type Stage = (typeof STAGES)[number]

export function stageOf(row: { choices: (string | null)[]; revealed: boolean }): Stage {
  if (row.revealed) return 'revealed'
  return row.choices.some((choice) => choice && choice !== 'idk') ? 'voted' : 'started'
}

/** The conversation filters behind each journey option, and back. */
export const JOURNEYS = ['started', 'voted', 'commented', 'revealed'] as const
type Journey = (typeof JOURNEYS)[number]
const JOURNEY_FILTERS: Record<Journey, Record<string, string>> = {
  started: { has_vote: 'false' },
  voted: { has_vote: 'true' },
  commented: { has_comment: 'true' },
  revealed: { revealed: 'true' }
}

export function journeyChanges(journey: string): Record<string, string | null> {
  return {
    has_vote: null,
    has_comment: null,
    revealed: null,
    ...JOURNEY_FILTERS[journey as Journey]
  }
}

export function journeyOf(params: URLSearchParams): string {
  if (params.get('revealed') === 'true') return 'revealed'
  if (params.get('has_comment') === 'true') return 'commented'
  if (params.get('has_vote') === 'false') return 'started'
  if (params.get('has_vote') === 'true') return 'voted'
  return ''
}

export function modelName(
  conversation: Pick<ActivityConversation, 'model_a' | 'model_b'>,
  side: Side
): string {
  return (
    (side === 'a' ? conversation.model_a : conversation.model_b)?.name ??
    m['admin.activity.conversation.unknownModel']()
  )
}

/** One answer of a turn, with the feedback left on it. */
export function answerOf(turn: ActivityTurn, side: Side) {
  return {
    answer: side === 'a' ? turn.answer_a : turn.answer_b,
    tags: side === 'a' ? turn.tags_a : turn.tags_b,
    comment: side === 'a' ? turn.comment_a : turn.comment_b,
    verdict: sideVerdict([turn.choice], side)
  }
}
