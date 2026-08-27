import { goto } from '$app/navigation'
import { resolve } from '$app/paths'
import { CaptchaError, consumeAltchaToken } from '$lib/captcha.svelte'
import { api, StreamTimeoutError, ValidationError } from '$lib/fastapi-client'
import type {
  Consumption as APIConsoData,
  RevealData as APIRevealData,
  ComparisonPublic,
  LLMMessageCreate,
  TurnPublic,
  UserMessageRead,
  LinkupSearchTextResult as WebSearchResults
} from '$lib/generated/backend'
import { m } from '$lib/i18n/messages'
import { COHORT_STORAGE_KEY } from '$lib/stores/cohortStore.svelte'
import { createContext } from 'svelte'
import { InternalError } from './fastapi-client'

export type { APIRevealData, WebSearchResults }

// PROMPT
export type Mode = 'random' | 'custom' | 'big-vs-small' | 'small-models'

export interface APIModeAndPromptData {
  prompt_value: string
  mode: Mode
  custom_models_selection: string[]
  web_search: boolean
}

export type ModeInfos = {
  value: Mode
  title: string
  label: string
  alt_label: string
  icon: string
  description: string
}

// COMPARISON

export type Bot = 'a' | 'b'

// Comparison overrides
export type UserMessage = UserMessageRead
export interface AssistantMessage extends LLMMessageCreate {
  content: string
}
export type AnyMessage = UserMessage | AssistantMessage
export interface APIComparisonTurn extends TurnPublic {
  user_msg: UserMessage
  llm_msg_a: AssistantMessage | null
  llm_msg_b: AssistantMessage | null
}
export interface APIComparison extends ComparisonPublic {
  turns: APIComparisonTurn[]
}

// FIXME get from backend constant
export const TURN_CHOICES = ['a_better', 'both_good', 'idk', 'both_bad', 'b_better'] as const
export type TurnChoice = (typeof TURN_CHOICES)[number]

export type ComparisonTurnStatus = 'pending' | 'generating' | 'error' | 'complete'
export type ComparisonStatus = ComparisonTurnStatus | 'revealed'

export interface ComparisonTurnSide {
  status: ComparisonTurnStatus
  llm_msg: AssistantMessage | null
  keyword_annotations: string[]
  custom_annotation: string
}
export interface ComparisonTurn extends Pick<APIComparisonTurn, 'id' | 'user_msg' | 'choice'> {
  a: ComparisonTurnSide
  b: ComparisonTurnSide
  status: ComparisonTurnStatus
}
export interface Comparison extends Omit<APIComparison, 'turns' | 'error'> {
  turns: ComparisonTurn[]
  error?: string
  reveal_data?: APIRevealData | null
}

// ANNOTATIONS
export interface VoteAnnotations {
  keyword_annotations: string[]
  custom_annotation: string
}
export interface APIVoteChoice {
  turn_id: string
  choice: TurnChoice
}

export interface APIVoteAnnotate {
  turn_id: string
  pos: Bot
  keyword_annotations: string[]
  custom_annotation: string
}

export type AnyAPIVote = APIVoteChoice | APIVoteAnnotate

// REVEAL
export interface RevealModelData extends APIConsoData {
  id: string
  pos: Bot
}

export interface RevealData {
  selected: Bot | null
  modelsData: RevealModelData[]
  shareB64Data: APIRevealData['b64']
}

// DATA

export const modeInfos: ModeInfos[] = (
  [
    { value: 'random', icon: 'i-ri-dice-line' },
    { value: 'custom', icon: 'i-ri-search-line' },
    { value: 'small-models', icon: 'i-ri-leaf-line' },
    { value: 'big-vs-small', icon: 'i-ri-ruler-line' }
  ] as const
).map((item) => ({
  ...item,
  title: m[`modes.${item.value}.title`](),
  label: m[`modes.${item.value}.label`](),
  alt_label: m[`modes.${item.value}.altLabel`](),
  description: m[`modes.${item.value}.description`]()
}))

// COMPARISON LOGIC

export type ComparisonsCtx = Comparison[]
export const [getComparisonsContext, setComparisonsContext] = createContext<ComparisonsCtx>()

function parseAPITurn(turn: APIComparisonTurn): ComparisonTurn {
  const status = !turn.llm_msg_a && !turn.llm_msg_b ? 'pending' : 'complete'
  return {
    id: turn.id,
    status,
    choice: turn.choice,
    user_msg: turn.user_msg,
    a: {
      status: !turn.llm_msg_a ? 'pending' : 'complete',
      llm_msg: turn.llm_msg_a,
      custom_annotation: '',
      keyword_annotations: []
    },
    b: {
      status: !turn.llm_msg_b ? 'pending' : 'complete',
      llm_msg: turn.llm_msg_b,
      custom_annotation: '',
      keyword_annotations: []
    }
  }
}

export function parseAPIComparison(
  comparison: APIComparison,
  recoverInterrupted = false
): Comparison {
  const parsed: Comparison = {
    ...comparison,
    error: comparison.error?.message,
    turns: comparison.turns.map(parseAPITurn)
  }

  // Data loaded by a fresh page is not attached to the old SSE request. Any
  // incomplete turn therefore cannot make further progress and must not be
  // presented as if it were still generating forever.
  const interruptedTurn = recoverInterrupted
    ? parsed.turns.findLast((turn) => turn.status === 'pending')
    : undefined
  if (interruptedTurn) {
    parsed.error ??= 'provider_error'
    interruptedTurn.status = 'error'
  }

  return parsed
}

export function parseAPIRevealData(data: APIRevealData): RevealData {
  return {
    selected: data.chosen_llm,
    modelsData: (['a', 'b'] as const).map((pos) => ({
      id: data[pos].llm_id,
      pos,
      ...data[pos].conso
    })),
    shareB64Data: data.b64
  }
}

export async function queryComparisons(_fetch: typeof fetch = fetch) {
  const data = await api.request<APIComparison[]>('/arena/comparison/list', { fetch: _fetch })
  return data.map((c) => parseAPIComparison(c, true))
}

export function initComparisonsContext(data: ComparisonsCtx) {
  const comparisons = $state(data)
  setComparisonsContext(comparisons)
}

export async function updateComparisonsContext(comparisons: ComparisonsCtx) {
  const data = await queryComparisons()
  comparisons.length = 0
  comparisons.push(...data)
}

export function getComparison<Id extends string | undefined>(comparisonId: Id) {
  const comparisons = getComparisonsContext()
  let comparisonId_ = $state<Id>(comparisonId)
  let loading = $state(false)
  let promptError = $state<string>()
  let promptWarnings = $state<string[]>()
  // Kept so "send anyway" resends the very same prompt: the backend serves the
  // verdict it already has for that text instead of moderating it again.
  let warnedRequest: { url: string; body: Record<string, unknown> } | undefined

  const comparison = $derived(
    comparisonId_ ? comparisons.find((c) => c.id === comparisonId_) : null
  )
  const errorMsg = $derived(comparison?.error)
  const turn = $derived(comparison?.turns[comparison.turns.length - 1])

  const status = $derived.by(() => {
    if (errorMsg || promptError) return 'error'
    if (!comparison || !turn) return 'pending'
    if (comparison.reveal_data) return 'revealed'
    return turn.status
  })

  async function ask(url: string, body: any): Promise<boolean> {
    loading = true
    promptError = undefined
    promptWarnings = undefined
    if (comparison) {
      comparison.error = undefined
    }

    let receivedEvent = false
    let warned = false
    try {
      const altcha_token = await consumeAltchaToken()

      for await (const event of api.stream(url, { ...body, altcha_token })) {
        receivedEvent = true
        if (event.type === 'warning') {
          warned = true
          warnedRequest = { url, body: { ...body, warning_token: event.warning_token } }
          promptWarnings = event.warnings.map((warning) => warning.message)
          break
        } else if (event.type === 'init') {
          const id = event.comparison.id.toString()
          comparisons.unshift(parseAPIComparison(event.comparison))
          comparisonId_ = id as Id
        } else {
          if (!comparison) throw new InternalError('No comparison to update')

          if (event.type === 'add') {
            comparison.turns.push(parseAPITurn(event.turn))
            goto(resolve(`/${comparisonId_ as string}`))
          } else {
            if (!turn) throw new InternalError('No turn to update')

            if (event.type === 'update') {
              comparison.turns[comparison.turns.length - 1] = parseAPITurn(event.turn)
              goto(resolve(`/${comparisonId_ as string}`))
            } else if (event.type === 'error') {
              if (event.pos) {
                turn[event.pos].status = 'error'
              }
              turn.status = 'error'
              comparison.error = event.error
            } else if (event.type === 'chunk') {
              turn.status = 'generating'
              turn[event.pos].status = 'generating'
              turn[event.pos].llm_msg = event.llm_msg
            } else if (event.type === 'complete') {
              if (event.pos) {
                turn[event.pos].status = 'complete'
              } else {
                turn.status = 'complete'
              }
            }
          }
        }
      }
      if (!receivedEvent && comparison) {
        // SSE opened with no events — backend crashed before its first yield.
        comparison.error = 'empty_stream'
        if (turn) turn.status = 'error'
      }
    } catch (err) {
      if (err instanceof ValidationError) {
        promptError = err.errors ? err.errors[0].msg : err.message
      } else if (err instanceof CaptchaError) {
        promptError = 'Vérification anti-robot indisponible, veuillez réessayer.'
      } else if (err instanceof StreamTimeoutError && comparison) {
        comparison.error = 'timeout'
        if (turn) turn.status = 'error'
      } else {
        throw err
      }
    } finally {
      loading = false
    }

    return !warned && !comparison?.error && !promptError
  }

  return {
    get comparison() {
      return comparison as Id extends string ? Comparison : Comparison | null
    },
    get comparisonId() {
      return comparisonId_
    },
    get status() {
      return status
    },
    get loading() {
      return loading
    },
    get error() {
      return errorMsg
    },
    get promptError() {
      return promptError
    },
    set promptError(v: string | undefined) {
      promptError = v
    },
    get promptWarnings() {
      return promptWarnings
    },

    /** User went back to edit: drop the warning, keep the prompt. */
    dismissWarnings() {
      promptWarnings = undefined
      warnedRequest = undefined
    },

    /** User chose to send anyway: same prompt, cached verdict, no second check. */
    async sendAnyway() {
      if (!warnedRequest) return false
      const { url, body } = warnedRequest
      warnedRequest = undefined
      return await ask(url, body)
    },

    async askFirst(args: APIModeAndPromptData) {
      const cohorts = sessionStorage.getItem(COHORT_STORAGE_KEY)
      if (cohorts === null) {
        console.error(
          `[COHORT] cohorts is None and it should not happen, maybe cohorts detection has not been called.`
        )
      } else if (cohorts) {
        console.debug(`[COHORT] call to '/arena/add_first_text' with found cohorts: '${cohorts}'`)
      }

      return await ask('/arena/add_first_text', {
        prompt_value: args.prompt_value,
        mode: args.mode,
        custom_models_selection: args.mode === 'custom' ? args.custom_models_selection : null,
        web_search: args.web_search,
        cohorts
      })
    },

    async ask(text: string) {
      if (!comparison?.turns.every((turn) => !!turn.choice)) return
      return await ask(`/arena/add_text/${comparisonId_}`, { message: text })
    },

    async retry() {
      return await ask(`/arena/retry/${comparisonId_}`, {})
    },

    async vote(data: AnyAPIVote) {
      await api.request<APIRevealData>(`/arena/vote/${comparisonId_}`, {
        method: 'POST',
        body: JSON.stringify(data)
      })
      const turn = comparison!.turns.find((t) => t.id === data.turn_id)!
      if ('choice' in data) {
        turn.choice = data.choice
      } else {
        turn[data.pos].custom_annotation = data.custom_annotation
        turn[data.pos].keyword_annotations = data.keyword_annotations
      }
    },

    async reveal() {
      if (!comparison) throw new InternalError('No comparison to reveal.')
      const revealData = await api.request<APIRevealData>(`/arena/reveal/${comparisonId_}`, {
        method: 'POST'
      })

      comparison.reveal_data = revealData
    }
  }
}
