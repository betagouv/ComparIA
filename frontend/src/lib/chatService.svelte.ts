import { api } from '$lib/api'
import { state, type Mode } from '$lib/state.svelte'
import type { LoadingStatus } from '@gradio/statustracker'

export interface ModeAndPromptData {
  prompt_value: string
  mode: Mode
  custom_models_selection: string[]
}

export interface APIVoteData {
  which_model_radio_output: 'model-a' | 'model-b' | 'both-equal'
  positive_a_output: string[]
  positive_b_output: string[]
  negative_a_output: string[]
  negative_b_output: string[]
  comments_a_output: string
  comments_b_output: string
}

export interface Model {
  // [aya-expanse-8b]
  // simple_name = "Aya Expanse 8B"
  // organisation = "Cohere"
  // icon_path = "cohere.png"
  // friendly_size = "S"
  // distribution = "open-weights"
  // conditions = "copyleft"
  // params = 8
  // license = "CC-BY-NC-4.0"
  // description = "Aya Expanse 8B de Cohere, entreprise canadienne, est un petit modèle de la famille Command R qui a spécialement été entraîné sur un corpus multilingue."

  id: string
  friendly_size: 'XS' | 'S' | 'M' | 'L' | 'XL' | 'XXL'
  simple_name: string
  organisation: string
  params: number
  total_params: number
  distribution: 'open-weights' | 'api-only'
  icon_path: string
  release_date: string | null
  fully_open_source: boolean
}

// MESSAGES

type APIMessageRole = 'system' | 'user' | 'assistant'
export type Bot = 'a' | 'b'

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

export const positiveReactions = ['useful', 'complete', 'creative', 'clear-formatting'] as const
export const negativeReactions = ['incorrect', 'superficial', 'instructions-not-followed'] as const

export type ReactionPref = (typeof positiveReactions)[number] | (typeof negativeReactions)[number]
export type ReactionKind = 'like' | 'comment'
export type APIReactionData = {
  index: number
  value: string
  liked?: boolean | null
  prefs?: ReactionPref[]
  comment?: string
}
export type OnReactionFn = (kind: ReactionKind, reaction: Required<APIReactionData>) => void

export const chatbot = $state<{
  status: LoadingStatus['status']
  messages: APIChatMessage[]
  root: string
}>({
  status: 'pending',
  messages: [],
  root: '/' // FIXME or '/arene'
})

export async function runChatBots(args: ModeAndPromptData) {
  chatbot.status = 'pending'

  try {
    const job = await api.submit<APIChatMessage[]>('/add_first_text', { model_dropdown_scoped: args })

    state.currentScreen = 'chatbots'
    state.mode = args.mode
    // FIXME get api data
    state.votes = { count: 1000, objective: 2000, ratio: 50 }
    state.step = 1
    // chatbot.status = 'streaming'

    for await (const messages of job) {
      chatbot.status = 'generating'
      chatbot.messages = messages
    }

    chatbot.status = 'complete'
  } catch (error) {
    console.error('Error:', error)
    chatbot.status = 'error'
  }

  return chatbot.status
}

export async function askChatBots(text: string) {
  chatbot.status = 'pending'

  try {
    const job = await api.submit<APIChatMessage[]>('/add_text', { text })
    // chatbot.status = 'streaming'

    for await (const messages of job) {
      chatbot.status = 'generating'
      chatbot.messages = messages
    }

    chatbot.status = 'complete'
  } catch (error) {
    console.error('Error:', error)
    chatbot.status = 'error'
  }
}
