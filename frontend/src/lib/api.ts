import { Client, type Payload } from '@gradio/client'

export async function submitFormData(text: string): Promise<boolean> {
  // Simulation d'un appel API avec délai
  return new Promise((resolve) => {
    setTimeout(() => {
      // Pour simuler une erreur aléatoire (20% de chance)
      const shouldFail = Math.random() < 0.2
      resolve(!shouldFail)
    }, 1500)
  })
}

export const api = {
  // FIXME connect to client only once?
  url: 'http://localhost:7860/',

  async connect() {
    console.debug('Connecting to Gradio at:', this.url)
    try {
      const client = await Client.connect(this.url)
      console.debug('Successfully connected to Gradio')
      return client
    } catch (error) {
      console.error('Failed to connect to Gradio:', error)
      throw error
    }
  },

  async submit(uri: string, params: any) {
    console.debug(`Submitting Gradio job '${uri}' with params:`, params)
    try {
      const client = await this.connect()
      const result = await client.submit(uri, params)
      console.debug('Gradio job submitted successfully')
      return result
    } catch (error) {
      console.error('Failed to submit Gradio job:', error)
      throw error
    }
  }
}

interface GradioMessage {
  role: 'user' | 'assistant'
  error: any
  content: string
}

export interface GradioResponse extends Payload {
  type: 'data'
  endpoint: string
  // Tuple de 10 éléments où seul le premier nous intéresse
  data: [Array<GradioMessage | any>, ...any[]]
}

export function parseGradioResponse(response: GradioResponse): Array<GradioMessage> {
  if (!response.data || !Array.isArray(response.data) || response.data.length === 0) {
    throw new Error('Invalid Gradio response format')
  }

  return response.data[0]
}
