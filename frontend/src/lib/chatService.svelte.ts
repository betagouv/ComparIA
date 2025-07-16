import { api } from '$lib/api'
import { state, type Mode } from '$lib/state.svelte'
import type { Message, NormalisedMessage } from '$lib/types'
import { update_messages } from '$lib/utils'
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

export const chatbot = $state<{
  status: LoadingStatus['status']
  messages: NormalisedMessage[]
  root: string
}>({
  status: 'pending',
  messages: [],
  root: '/' // FIXME or '/arene'
})

export async function runChatBots(args: ModeAndPromptData) {
  chatbot.status = 'pending'

  try {
    const job = await api.submit<Message[]>('/add_first_text', { model_dropdown_scoped: args })

    state.currentScreen = 'chatbots'
    state.mode = args.mode
    // FIXME get api data
    state.votes = { count: 1000, objective: 2000, ratio: 50 }
    state.step = 1
    // chatbot.status = 'streaming'

    for await (const messages of job) {
      chatbot.status = 'generating'
      chatbot.messages = update_messages(messages, chatbot.messages, chatbot.root)
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
    const job = await api.submit<Message[]>('/add_text', { text })
    // chatbot.status = 'streaming'

    for await (const messages of job) {
      chatbot.status = 'generating'
      chatbot.messages = update_messages(messages, chatbot.messages, chatbot.root)
    }

    chatbot.status = 'complete'
  } catch (error) {
    console.error('Error:', error)
    chatbot.status = 'error'
  }
}
