import { Client } from '@gradio/client'

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

export async function connectToGradio(url: string) {
  console.log('Connecting to Gradio at:', url)
  try {
    const client = await Client.connect(url)
    console.log('Successfully connected to Gradio')
    return client
  } catch (error) {
    console.error('Failed to connect to Gradio:', error)
    throw error
  }
}

export async function submitGradioJob(
  app: any,
  modelParams: {
    mode: string
    custom_models_selection: any[]
    prompt_value: string
  }
) {
  console.log('Submitting Gradio job with params:', modelParams)
  try {
    const result = await app.submit('/add_first_text', [modelParams])
    console.log('Gradio job submitted successfully')
    return result
  } catch (error) {
    console.error('Failed to submit Gradio job:', error)
    throw error
  }
}

interface GradioMessage {
  role: 'user' | 'assistant'
  error: any
  content: string
}

interface GradioResponse {
  type: string
  time: Date
  // Tuple de 10 éléments où seul le premier nous intéresse
  data: [Array<Array<GradioMessage | any>>, ...any[]]
  endpoint: string
  fn_index: number
}

export function parseGradioResponse(response: GradioResponse): Array<Array<GradioMessage>> {
  if (!response.data || !Array.isArray(response.data) || response.data.length === 0) {
    throw new Error('Invalid Gradio response format')
  }

  return response.data[0]
}
