import type {
  ModelFilter,
  SelectionModeAdmin,
  SelectionModeDraft,
  SelectionModeRules,
  SelectionModeUpsert
} from '$lib/generated/admin'
import type { ModeIcons } from '$lib/generated/constants'
import type { getLocalesContext } from '$lib/global.svelte'
import { m } from '$lib/i18n/messages'
import type { Locale } from '$lib/i18n/runtime'
import type { Option } from '$lib/utils/form'

export type Pairing = NonNullable<SelectionModeRules['pairing']>
export type Sampling = NonNullable<SelectionModeRules['sampling']>
export type ToolsPolicy = NonNullable<SelectionModeRules['tools_policy']>
export type VisitorPicks = NonNullable<SelectionModeRules['visitor_picks']>

type RowFields = 'id' | 'created_at' | 'updated_at' | 'position'

/** What the editor holds. Dates stay as the text of a datetime-local input. */
export type ModeForm = Required<Omit<SelectionModeUpsert, RowFields | 'starts_at' | 'ends_at'>> &
  Pick<SelectionModeUpsert, RowFields> & { starts_at: string; ends_at: string }

export const ROW_FIELDS: RowFields[] = ['id', 'created_at', 'updated_at', 'position']

/** The choices of the fields shown as radio buttons, each with its help line. */
export const MODE_CHOICES: Record<
  'visitor_picks' | 'pairing' | 'sampling' | 'tools_policy',
  () => Option<string | number>[]
> = {
  visitor_picks: () =>
    [
      {
        value: 0,
        label: m['admin.selectionModes.picks.none'](),
        help: m['admin.selectionModes.picks.noneHelp']()
      },
      {
        value: 1,
        label: m['admin.selectionModes.picks.one'](),
        help: m['admin.selectionModes.picks.oneHelp']()
      },
      {
        value: 2,
        label: m['admin.selectionModes.picks.two'](),
        help: m['admin.selectionModes.picks.twoHelp']()
      }
    ] satisfies Option<VisitorPicks>[],
  pairing: () =>
    [
      {
        value: 'any',
        label: m['admin.selectionModes.pairing.any'](),
        help: m['admin.selectionModes.pairing.anyHelp']()
      },
      {
        value: 'different_lab',
        label: m['admin.selectionModes.pairing.differentLab'](),
        help: m['admin.selectionModes.pairing.differentLabHelp']()
      },
      {
        value: 'same_lab',
        label: m['admin.selectionModes.pairing.sameLab'](),
        help: m['admin.selectionModes.pairing.sameLabHelp']()
      },
      {
        value: 'different_size_class',
        label: m['admin.selectionModes.pairing.differentSize'](),
        help: m['admin.selectionModes.pairing.differentSizeHelp']()
      },
      {
        value: 'same_size_class',
        label: m['admin.selectionModes.pairing.sameSize'](),
        help: m['admin.selectionModes.pairing.sameSizeHelp']()
      }
    ] satisfies Option<Pairing>[],
  sampling: () =>
    [
      {
        value: 'uniform',
        label: m['admin.selectionModes.sampling.uniform'](),
        help: m['admin.selectionModes.sampling.uniformHelp']()
      },
      {
        value: 'fewer_votes',
        label: m['admin.selectionModes.sampling.fewerVotes'](),
        help: m['admin.selectionModes.sampling.fewerVotesHelp']()
      },
      {
        value: 'newest',
        label: m['admin.selectionModes.sampling.newest'](),
        help: m['admin.selectionModes.sampling.newestHelp']()
      }
    ] satisfies Option<Sampling>[],
  tools_policy: () =>
    [
      {
        value: 'visitor',
        label: m['admin.selectionModes.tools.visitor'](),
        help: m['admin.selectionModes.tools.visitorHelp']()
      },
      {
        value: 'none',
        label: m['admin.selectionModes.tools.none'](),
        help: m['admin.selectionModes.tools.noneHelp']()
      },
      {
        value: 'forced',
        label: m['admin.selectionModes.tools.forced'](),
        help: m['admin.selectionModes.tools.forcedHelp']()
      }
    ] satisfies Option<ToolsPolicy>[]
}

/** A mode's name in the admin's language, else the default one, else its key. */
export function modeLabel(
  mode: Pick<SelectionModeAdmin, 'key' | 'label'>,
  locales: ReturnType<typeof getLocalesContext>
): string {
  return mode.label[locales.current] ?? mode.label[locales.default] ?? mode.key
}

export const DEFAULT_ICON: ModeIcons = 'i-ri-dice-line'

// The server stores naive UTC times; the input shows them as they are.
function toInput(value?: string | null): string {
  return value ? value.slice(0, 16) : ''
}

function fromInput(value: string): string | null {
  return value ? `${value}:00` : null
}

// The values may be reactive proxies, which structuredClone refuses.
function copy<T>(value: T): T {
  return JSON.parse(JSON.stringify(value))
}

export function toForm(mode: SelectionModeAdmin | SelectionModeDraft): ModeForm {
  const row = mode as Partial<SelectionModeAdmin>
  return {
    key: mode.key ?? '',
    label: copy(mode.label ?? {}),
    short_label: copy(mode.short_label ?? {}),
    description: copy(mode.description ?? {}),
    // A saved mode may hold an icon that has since left the list
    icon: (mode.icon as ModeIcons) || DEFAULT_ICON,
    enabled: row.enabled ?? true,
    is_default: row.is_default ?? false,
    visitor_picks: mode.visitor_picks ?? 0,
    pool_a: copy(mode.pool_a ?? {}),
    pool_b: mode.pool_b ? copy(mode.pool_b) : null,
    pairing: mode.pairing ?? 'any',
    sampling: mode.sampling ?? 'uniform',
    tools_policy: mode.tools_policy ?? 'visitor',
    tool_keys: [...(mode.tool_keys ?? [])],
    cohorts: [...(row.cohorts ?? [])],
    locales: [...((row.locales ?? []) as Locale[])],
    starts_at: toInput(row.starts_at),
    ends_at: toInput(row.ends_at)
  }
}

function isEmpty(value: unknown): boolean {
  return (
    value === undefined ||
    value === null ||
    value === '' ||
    (typeof value === 'number' && Number.isNaN(value)) ||
    (Array.isArray(value) && value.length === 0)
  )
}

/**
 * The filter with every unset criterion left out. A cleared number input
 * hands back '' or null; the server wants the field absent or a number.
 */
export function cleanFilter(filter: ModelFilter): ModelFilter {
  const entries = Object.entries(filter).filter(([key, value]) => {
    if (key === 'tags_match') return value === 'all' && !!filter.tags?.length
    return !isEmpty(value)
  })
  return Object.fromEntries(
    entries.map(([key, value]) => [
      key,
      typeof value === 'string' && NUMERIC_FIELDS.has(key) ? Number(value) : value
    ])
  ) as ModelFilter
}

const NUMERIC_FIELDS = new Set([
  'params_min',
  'params_max',
  'released_within_days',
  'price_out_max',
  'top_ranked'
])

function trimmed(values: Record<string, string>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(values)
      .map(([locale, text]) => [locale, (text ?? '').trim()])
      .filter(([, text]) => text)
  )
}

/** What the draw reads, for the live preview. */
export function toRules(form: ModeForm): SelectionModeRules {
  return {
    visitor_picks: form.visitor_picks,
    pool_a: cleanFilter(form.pool_a),
    pool_b: form.pool_b ? cleanFilter(form.pool_b) : null,
    pairing: form.pairing,
    sampling: form.sampling,
    tools_policy: form.tools_policy,
    tool_keys: form.tools_policy === 'none' ? [] : [...form.tool_keys]
  }
}

export function toUpsert(form: ModeForm): SelectionModeUpsert {
  return {
    ...toRules(form),
    key: form.key.trim(),
    label: trimmed(form.label),
    short_label: trimmed(form.short_label),
    description: trimmed(form.description),
    icon: form.icon,
    enabled: form.enabled,
    is_default: form.is_default,
    cohorts: form.cohorts,
    locales: form.locales,
    starts_at: fromInput(form.starts_at),
    ends_at: fromInput(form.ends_at)
  }
}

/** A key from a label: lowercase ASCII, words joined by dashes. */
export function toModeKey(label: string): string {
  return label
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 50)
    .replace(/-+$/, '')
}

/** The key, with a number added when another mode already uses it. */
export function uniqueModeKey(base: string, taken: string[]): string {
  const key = base || 'mode'
  if (!taken.includes(key)) return key
  let n = 2
  while (taken.includes(`${key}-${n}`)) n++
  return `${key}-${n}`
}

type Audience = Pick<
  SelectionModeAdmin,
  'enabled' | 'cohorts' | 'locales' | 'starts_at' | 'ends_at' | 'viability'
>

/** Dates come back as naive UTC, as the backend stores them. */
function utc(value: string): number {
  return Date.parse(/Z|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`)
}

/**
 * Whether any visitor is offered the mode right now: switched on, able to
 * draw, and limited to no cohort, language or time window it is outside of.
 */
export function openToEveryone(mode: Audience, now = Date.now()): boolean {
  return (
    !!mode.enabled &&
    mode.viability.viable &&
    !mode.cohorts?.length &&
    !mode.locales?.length &&
    (!mode.starts_at || utc(mode.starts_at) <= now) &&
    (!mode.ends_at || now < utc(mode.ends_at))
  )
}
