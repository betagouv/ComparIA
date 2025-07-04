import { api } from '$lib/api'
import { state } from '$lib/state.svelte'
import type { Message, NormalisedMessage } from '$lib/types'
import { update_messages } from '$lib/utils'
import type { Payload } from '@gradio/client'
import type { LoadingStatus } from '@gradio/statustracker'
import type { ModeAndPromptData } from './utils-customdropdown'

export interface GradioResponse extends Payload {
  type: 'data'
  endpoint: string
  // Tuple de 10 éléments où seul le premier nous intéresse
  data: [Array<Message | any>, ...any[]]
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

export function parseGradioResponse(response: GradioResponse): Message[] {
  if (!response.data || !Array.isArray(response.data) || response.data.length === 0) {
    throw new Error('Invalid Gradio response format')
  }

  return response.data[0]
}

export async function runChatBots(args: ModeAndPromptData) {
  chatbot.status = 'pending'

  try {
    const job = await api.submit('/add_first_text', { model_dropdown_scoped: args })

    state.currentScreen = 'chatbots'
    state.mode = args.mode
    // FIXME get api data
    state.votes = { count: 1000, objective: 2000, ratio: 50 }
    state.step = 1
    chatbot.status = 'streaming'

    for await (const message of job) {
      console.log('msg', message)
      if (message.type === 'data') {
        chatbot.status = 'generating'
        const messages = parseGradioResponse(message as GradioResponse)
        chatbot.messages = update_messages(messages, chatbot.messages, chatbot.root)
      }
    }
    chatbot.status = 'complete'
  } catch (error) {
    console.error('Error:', error)
    chatbot.status = 'error'
  }

  return chatbot.status
}
