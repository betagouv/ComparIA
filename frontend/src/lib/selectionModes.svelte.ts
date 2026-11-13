import { api } from '$lib/fastapi-client'
import type { SelectionModePublic } from '$lib/generated/backend'
import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
import { m } from '$lib/i18n/messages'
import { getLocale } from '$lib/i18n/runtime'
import { storedCohorts } from '$lib/stores/cohortStore.svelte'
import { createContext, onMount } from 'svelte'

export type SelectionMode = SelectionModePublic

/** What the arena load hands down: the modes and how they were fetched. */
export interface LoadedSelectionModes {
  modes: SelectionMode[]
  cohorts: string
  /** The request failed and `modes` holds the built-in entry. */
  fallback: boolean
}

/**
 * A blind draw from every model, for when the modes cannot be loaded. It is
 * sent as a null mode, which the backend reads as its own default mode.
 */
export function fallbackModes(toolKeys: string[]): SelectionMode[] {
  return [
    {
      key: 'random',
      label: m['arenaHome.selectModels.fallback.label'](),
      short_label: m['arenaHome.selectModels.fallback.shortLabel'](),
      description: m['arenaHome.selectModels.fallback.description'](),
      icon: 'i-ri-dice-line',
      is_default: true,
      visitor_picks: 0,
      tools_policy: 'visitor',
      tool_keys: toolKeys,
      llm_ids: null
    }
  ]
}

export async function fetchSelectionModes(
  fetch: typeof globalThis.fetch,
  cohorts: string
): Promise<SelectionMode[]> {
  const searchParams: Record<string, string> = { locale: getLocale() }
  if (cohorts) searchParams.cohorts = cohorts
  return await api.request<SelectionMode[]>('/arena/selection-modes', { fetch, searchParams })
}

/** The remembered mode if it is still on offer, else the default one. */
export function pickCurrentMode(modes: SelectionMode[], storedKey: string): SelectionMode {
  return (
    modes.find((mode) => mode.key === storedKey) ??
    modes.find((mode) => mode.is_default) ??
    modes[0]
  )
}

/**
 * The models a mode still lets the visitor keep, trimmed to its pick limit.
 * A mode with two pools keeps a second pick only from the other pool.
 */
export function keepPickable(selection: string[], mode: SelectionMode): string[] {
  if (!mode.visitor_picks || !mode.llm_ids) return []
  const pool = mode.llm_ids
  const [first, second] = selection.filter((id) => pool.includes(id)).slice(0, mode.visitor_picks)
  if (first === undefined) return []
  if (second === undefined) return [first]
  const { llm_ids_a: a, llm_ids_b: b } = mode
  const facing =
    !a ||
    !b ||
    (a.includes(first) && b.includes(second)) ||
    (b.includes(first) && a.includes(second))
  return facing ? [first, second] : [first]
}

/** The tools a mode lets the visitor keep. A forced mode decides on its own. */
export function keepAllowedTools(selection: string[], mode: SelectionMode): string[] {
  if (mode.tools_policy === 'forced') return [...mode.tool_keys]
  if (mode.tools_policy === 'none') return []
  return selection.filter((key) => mode.tool_keys.includes(key))
}

export interface SelectionModesCtx {
  readonly modes: SelectionMode[]
  /** The mode the visitor is on: the remembered one if still offered, else the default. */
  readonly current: SelectionMode
  /** The key to send with a first message, null for the built-in entry. */
  readonly currentKey: string | null
  find(key: string | null | undefined): SelectionMode | undefined
  select(key: string): void
  selectDefault(): void
  refresh(): Promise<void>
}

export const [getSelectionModesContext, setSelectionModesContext] =
  createContext<SelectionModesCtx>()

/**
 * `loaded.cohorts` are the cohorts the load asked for. Cohorts kept in the
 * tab's session storage are only known after mount: when they differ, the
 * modes are fetched again so cohort modes show up.
 */
export function initSelectionModesContext(loaded: LoadedSelectionModes): SelectionModesCtx {
  let modes = $state(loaded.modes)
  let fallback = $state(loaded.fallback)
  const stored = useLocalStorage<string>('mode', '')
  const current = $derived(pickCurrentMode(modes, stored.value))

  async function refresh() {
    try {
      const fetched = await fetchSelectionModes(fetch, storedCohorts())
      if (!fetched.length) return
      modes = fetched
      fallback = false
    } catch (error) {
      // Keep the menu the visitor already has.
      console.error(`Unable to refresh selection modes: ${(error as Error).message}`)
    }
  }

  onMount(() => {
    if (storedCohorts() !== loaded.cohorts) refresh()
  })

  const ctx: SelectionModesCtx = {
    get modes() {
      return modes
    },
    get current() {
      return current
    },
    get currentKey() {
      return fallback ? null : current.key
    },
    find(key) {
      return modes.find((mode) => mode.key === key)
    },
    select(key) {
      stored.value = key
    },
    selectDefault() {
      stored.value = pickCurrentMode(modes, '').key
    },
    refresh
  }
  setSelectionModesContext(ctx)
  return ctx
}
