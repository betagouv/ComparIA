import { arenaApi } from '$lib/arena-api'
import { m } from '$lib/i18n/messages'
import type { APIBotModel, BotModel } from '$lib/models'
import { parseModel } from '$lib/models'
import type { LoadingStatus } from '@gradio/statustracker'

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

type APIMessageRole = 'system' | 'user' | 'assistant'
export type Bot = 'a' | 'b'
export type BotChoice = Bot | 'both_equal'

interface APIChatMessageMetadata<Role extends APIMessageRole = APIMessageRole> {
  bot: Role extends 'assistant' ? Bot : null
  duration: number | null
  generation_id: Role extends 'assistant' ? string : null
}

export interface APIChatMessage<Role extends APIMessageRole = APIMessageRole> {
  role: Role
  error: string | null
  metadata: APIChatMessageMetadata<Role>
  content: string
  reasoning: Role extends 'assistant' ? string | '' : null
}

export interface ChatMessage<Role extends APIMessageRole = APIMessageRole>
  extends APIChatMessage<Role> {
  index: number
  isLast: boolean
}

export type GroupedChatMessages = {
  user: ChatMessage<'user'>
  bots: [ChatMessage<'assistant'>, ChatMessage<'assistant'>]
}

// REACTIONS

// TODO use underscore everywhere ?
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

type DurationUnit = 'j' | 'h' | 'min' | 's'

interface APIConsoData {
  kwh: number
  co2: number
  tokens: number
  streaming: { value: number; unit: DurationUnit }
  lightbulb: { value: number; unit: DurationUnit }
}

interface APIRevealModelData {
  llm: APIBotModel
  conso: APIConsoData
}

export interface APIRevealData {
  b64: string
  chosen_model: BotChoice
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
    status: LoadingStatus['status']
    messages: APIChatMessage[]
    root: string
  }
}>({
  currentScreen: 'prompt',
  chat: {
    step: 1,
    status: 'pending',
    messages: [],
    root: '/' // FIXME or '/arene'
  }
})

// API CALLS

export async function runChatBots(args: APIModeAndPromptData) {
  arena.chat.status = 'pending'

  try {
    // Use new FastAPI client
    const customModels =
      args.mode === 'custom' && args.custom_models_selection.length === 2
        ? (args.custom_models_selection as [string, string])
        : undefined

    arena.currentScreen = 'chat'
    arena.mode = args.mode
    arena.chat.step = 1

    // Stream from FastAPI endpoint
    for await (const event of arenaApi.addFirstText(args.prompt_value, args.mode, customModels)) {
      if (event.type === 'init') {
        // Session initialized, continue streaming
        arena.chat.status = 'generating'
      } else if (event.type === 'update' && event.a && event.b) {
        // Merge messages from both models
        arena.chat.status = 'generating'
        // Combine messages from both sides
        const messagesA = event.a.messages || []
        const messagesB = event.b.messages || []
        // Interleave or merge as needed - for now just concatenate unique messages
        arena.chat.messages = mergeMessages(messagesA, messagesB)
      } else if (event.type === 'chunk' && event.messages) {
        // Single chunk update
        arena.chat.status = 'generating'
        arena.chat.messages = event.messages
      }
    }

    arena.chat.status = 'complete'
  } catch (error) {
    console.error('Error:', error)
    arena.chat.status = 'error'
  }

  return arena.chat.status
}

/**
 * Merge messages from both models into a single array.
 * Messages are deduplicated by role and content.
 */
function mergeMessages(messagesA: any[], messagesB: any[]): APIChatMessage[] {
  return messagesA
    .map((m, i) => {
      if (m.role === 'user') return m
      return [m, messagesB[i]]
    })
    .flat()
}

export async function askChatBots(text: string) {
  arena.chat.status = 'pending'

  try {
    // Stream from FastAPI endpoint
    for await (const event of arenaApi.addText(text)) {
      if (event.type === 'update' && event.a && event.b) {
        arena.chat.status = 'generating'
        const messagesA = event.a.messages || []
        const messagesB = event.b.messages || []
        arena.chat.messages = mergeMessages(messagesA, messagesB)
      } else if (event.type === 'chunk' && event.messages) {
        arena.chat.status = 'generating'
        arena.chat.messages = event.messages
      }
    }

    arena.chat.status = 'complete'
  } catch (error) {
    console.error('Error:', error)
    arena.chat.status = 'error'
  }
}

export async function retryAskChatBots() {
  arena.chat.status = 'pending'

  try {
    // Stream from FastAPI endpoint
    for await (const event of arenaApi.retry()) {
      if (event.type === 'update' && event.a && event.b) {
        arena.chat.status = 'generating'
        const messagesA = event.a.messages || []
        const messagesB = event.b.messages || []
        arena.chat.messages = mergeMessages(messagesA, messagesB)
      } else if (event.type === 'chunk' && event.messages) {
        arena.chat.status = 'generating'
        arena.chat.messages = event.messages
      }
    }

    arena.chat.status = 'complete'
  } catch (error) {
    console.error('Error:', error)
    arena.chat.status = 'error'
  }
}

export async function updateReaction(reaction: APIReactionData) {
  // Use fastapiClient which handles full backend URL
  const { fastapiClient } = await import('./fastapi-client')
  await fastapiClient.request('/arena/react', {
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

  // Use fastapiClient which handles full backend URL
  const { fastapiClient } = await import('./fastapi-client')

  const revealData = await fastapiClient.request<APIRevealData>('/arena/vote', {
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
    selected: data.chosen_model ?? 'both_equal',
    modelsData: (['a', 'b'] as const).map((pos) => ({
      model: parseModel(data[pos].llm),
      pos,
      ...data[pos].conso,
      co2: data[pos].conso.co2 * 1000 // FIXME *1000?
    })),
    shareB64Data: data.b64
  }
}

export async function getReveal(): Promise<RevealData> {
  const sessionHash = arenaApi.getSessionHash()
  if (!sessionHash) {
    throw new Error('No session hash available')
  }

  // Use fastapiClient which handles full backend URL
  const { fastapiClient } = await import('./fastapi-client')

  const revealData = await fastapiClient.request<APIRevealData>(`/arena/reveal/${sessionHash}`, {
    method: 'GET'
  })

  return parseAPIRevealData(revealData)
}
