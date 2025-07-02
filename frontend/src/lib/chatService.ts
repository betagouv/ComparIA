import { get } from 'svelte/store'
import { connectToGradio, parseGradioResponse, submitGradioJob } from './api'
import { conversation, customModelsDropdown, hasError, isLoading, mode, textValue } from './stores'

type ModelParams = {
  mode: string
  custom_models_selection: string[]
  prompt_value: string
}

export async function sendChatMessage() {
  isLoading.set(true)
  hasError.set(false)
  const currentTextValue = get(textValue)
  const currentMode = get(mode) as string
  const currentModels = get(customModelsDropdown) as string[]

  try {
    const app = await connectToGradio('http://localhost:7860/')
    const modelParams: ModelParams = {
      mode: currentMode,
      custom_models_selection: currentModels,
      prompt_value: currentTextValue
    }

    const job = await submitGradioJob(app, modelParams)

    for await (const message of job) {
      if (message.type === 'data') {
        const messages = parseGradioResponse(message)
        const chatbot1Messages = Array.isArray(messages[0]) ? messages[0] : []
        const chatbot2Messages =
          messages.length > 1 && Array.isArray(messages[1]) ? messages[1] : []

        conversation.update((conv) => ({
          chatbot1: chatbot1Messages,
          chatbot2: chatbot2Messages
        }))
      }
    }
  } catch (error) {
    console.error('Error:', error)
    hasError.set(true)
  } finally {
    isLoading.set(false)
  }
}
