import { state } from '$lib/state.svelte'
import { Client } from '@gradio/client'

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
    state.loading = true
    console.debug(`Submitting Gradio job '${uri}' with params:`, params)

    try {
      const client = await this.connect()
      const result = await client.submit(uri, params)
      console.debug('Gradio job submitted successfully')
      return result
    } catch (error) {
      console.error('Failed to submit Gradio job:', error)
      throw error
    } finally {
      state.loading = false
    }
  }
}
