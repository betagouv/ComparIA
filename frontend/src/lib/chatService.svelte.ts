import { api, ValidationError, type AnySSEEvent } from '$lib/fastapi-client'
import { m } from '$lib/i18n/messages'
import type { APIBotModel, BotModel } from '$lib/models'
import { parseModel } from '$lib/models'
import { COHORT_STORAGE_KEY } from '$lib/stores/cohortStore.svelte'

// PROMPT
export type Mode = 'random' | 'custom' | 'big-vs-small' | 'small-models'

export interface APIModeAndPromptData {
  prompt_value: string
  mode: Mode
  custom_models_selection: string[]
}

export type ModeInfos = {
  value: Mode
  title: string
  label: string
  alt_label: string
  icon: string
  description: string
}

// CHAT

export type Bot = 'a' | 'b'
export type BotChoice = Bot | 'both_equal'

export type LLMPos = 'a' | 'b'
export type ChatStatus = 'pending' | 'error' | 'complete' | 'generating'

export interface UserMessage {
  role: 'user'
  content: string
  error: { round_index: number; pos: Bot; content: string } | null
}
export interface AssistantMessage {
  role: 'assistant'
  pos: Bot
  metadata: {
    bot: Bot
    duration: number | null
    generation_id: string
  }
  content: string
  reasoning: string | ''

  generating?: boolean
}
export type AnyMessage = UserMessage | AssistantMessage

interface Chat {
  messages: AnyMessage[]
  status: ChatStatus
  // error: string | null
}
export interface ChatRound {
  user: UserMessage
  a?: AssistantMessage
  b?: AssistantMessage
  showMessages: boolean
  index: number
}

// REACTIONS

export const APIPositiveReactions = ['useful', 'complete', 'creative', 'clear_formatting'] as const
export const APINegativeReactions = [
  'incorrect',
  'superficial',
  'instructions_not_followed'
] as const
export type APIReactionPref =
  | (typeof APIPositiveReactions)[number]
  | (typeof APINegativeReactions)[number]

export type ReactionKind = 'like' | 'comment'
export type APIReactionData = {
  bot: Bot
  index: number
  value: string
  liked: boolean | null
  prefs: APIReactionPref[]
  comment?: string
}
export type OnReactionFn = (reaction: APIReactionData) => void

// VOTE

export interface APIVoteData {
  chosen_llm: BotChoice
  prefs_a: APIReactionPref[]
  prefs_b: APIReactionPref[]
  comment_a: string
  comment_b: string
}

interface VoteDetails {
  like: APIReactionPref[]
  dislike: APIReactionPref[]
  comment: string
}
export interface VoteData {
  selected?: BotChoice
  a: VoteDetails
  b: VoteDetails
}

// REVEAL

type DurationUnit = 'j' | 'h' | 'min' | 's' | 'ms'

type CO2Unit = 'g' | 'mg'

type EnergyUnit = 'Wh' | 'mWh'

interface APIConsoData {
  tokens: number
  energy: { value: number; unit: EnergyUnit }
  co2: { value: number; unit: CO2Unit }
  streaming: { value: number; unit: DurationUnit }
  lightbulb: { value: number; unit: DurationUnit }
  // deprecated: kept for backward compatibility
  kwh: number
}

interface APIRevealModelData {
  llm: APIBotModel
  conso: APIConsoData
}

export interface APIRevealData {
  b64: string
  chosen_llm: BotChoice
  a: APIRevealModelData
  b: APIRevealModelData
}

interface RevealModelData extends APIConsoData {
  model: BotModel
  pos: Bot
}
export interface RevealData {
  selected: BotChoice
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

export const arena = $state<{
  currentScreen: 'prompt' | 'chat'
  mode?: Mode
  chat: {
    step?: 1 | 2
    status: ChatStatus
    a: Chat
    b: Chat
    error: string | null
  }
}>({
  currentScreen: 'prompt',
  chat: {
    step: 1,
    status: 'pending',
    a: { status: 'pending', messages: [] },
    b: { status: 'pending', messages: [] },
    error: null
  }
})

// API CALLS

function onSSEEvent(event: AnySSEEvent) {
  if (event.type === 'init') {
    arena.chat.status = 'pending'
  } else if (event.type === 'error') {
    arena.chat.error = event.error
    arena.chat.status = 'error'
    if (event.pos) {
      arena.chat[event.pos].status = 'error'
    }
  } else if (event.type === 'chunk') {
    arena.chat[event.pos].messages = event.messages
    arena.chat[event.pos].status = 'generating'
    arena.chat.status = 'generating'
  } else if (event.type === 'complete') {
    if (event.pos) {
      arena.chat[event.pos].status = 'complete'
    } else {
      arena.chat.status = 'complete'
    }
  }
}

export async function runChatBots(args: APIModeAndPromptData): Promise<string | undefined> {
  arena.chat.status = 'pending'
  arena.chat.error = null

  try {
    const cohorts = sessionStorage.getItem(COHORT_STORAGE_KEY)
    if (cohorts === null) {
      console.error(
        `[COHORT] cohorts is None and it should not happen, maybe cohorts detection has not been called.`
      )
    }
    if (cohorts) {
      console.debug(`[COHORT] call to '/arena/add_first_text' with found cohorts: '${cohorts}'`)
    }

    const stream = api.stream('/arena/add_first_text', {
      prompt_value: args.prompt_value,
      mode: args.mode,
      custom_models_selection: args.custom_models_selection,
      cohorts
    })

    // Stream from FastAPI endpoint
    for await (const event of stream) {
      if (arena.currentScreen !== 'chat') {
        arena.currentScreen = 'chat'
        arena.mode = args.mode
        arena.chat.step = 1
      }
      onSSEEvent(event)
    }

    arena.chat.status = arena.chat.status = [
      arena.chat.status,
      arena.chat.a.status,
      arena.chat.b.status
    ].some((status) => status === 'error')
      ? 'error'
      : 'complete'
  } catch (error) {
    if (error instanceof ValidationError) {
      arena.chat.status = 'complete'
      return error.message
    }
    arena.chat.status = 'error'
    throw error
  }

  return arena.chat.status
}

export async function askChatBots(text: string): Promise<string | undefined> {
  arena.chat.status = 'pending'
  arena.chat.error = null
  try {
    // Stream from FastAPI endpoint
    for await (const event of api.stream('/arena/add_text', {
      message: text
    })) {
      onSSEEvent(event)
    }

    arena.chat.status = arena.chat.status = [
      arena.chat.status,
      arena.chat.a.status,
      arena.chat.b.status
    ].some((status) => status === 'error')
      ? 'error'
      : 'complete'
  } catch (error) {
    if (error instanceof ValidationError) {
      arena.chat.status = 'complete'
      return error.message
    }
    arena.chat.status = 'error'
    throw error
  }
}

export async function retryAskChatBots(): Promise<string | undefined> {
  arena.chat.status = 'pending'
  arena.chat.error = null
  try {
    // Stream from FastAPI endpoint
    for await (const event of api.stream('/arena/retry', {})) {
      onSSEEvent(event)
    }

    arena.chat.status = arena.chat.status = [
      arena.chat.status,
      arena.chat.a.status,
      arena.chat.b.status
    ].some((status) => status === 'error')
      ? 'error'
      : 'complete'
  } catch (error) {
    if (error instanceof ValidationError) {
      arena.chat.status = 'complete'
      return error.message
    }
    arena.chat.status = 'error'
    throw error
  }
}

export async function updateReaction(reaction: APIReactionData) {
  await api.request('/arena/react', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(reaction)
  })
}

export async function postVoteGetReveal(vote: Required<VoteData>) {
  const data = {
    chosen_llm: vote.selected,
    prefs_a: [...vote.a.like, ...vote.a.dislike],
    prefs_b: [...vote.b.like, ...vote.b.dislike],
    comment_a: vote.a.comment,
    comment_b: vote.b.comment
  } satisfies APIVoteData

  const revealData = await api.request<APIRevealData>('/arena/vote', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })

  return parseAPIRevealData(revealData)
}

function parseAPIRevealData(data: APIRevealData): RevealData {
  return {
    selected: data.chosen_llm,
    modelsData: (['a', 'b'] as const).map((pos) => ({
      model: parseModel(data[pos].llm),
      pos,
      ...data[pos].conso
    })),
    shareB64Data: data.b64
  }
}

export async function getReveal(): Promise<RevealData> {
  const revealData = await api.request<APIRevealData>(`/arena/reveal`, {
    method: 'GET'
  })

  return parseAPIRevealData(revealData)
}
