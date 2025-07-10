import { env } from '$env/dynamic/public'
import { state } from '$lib/state.svelte'
import { Client } from '@gradio/client'

export const api = {
  // FIXME connect to client only once?
  url: env.PUBLIC_API_URL || '/api',
  client: undefined as Client | undefined,

  async _connect() {
    if (this.client) return this.client
    console.debug('Connecting to Gradio at:', this.url)
    try {
      this.client = await Client.connect(this.url)
      console.debug('Successfully connected to Gradio')
      return this.client
    } catch (error) {
      console.error('Failed to connect to Gradio:', error)
      throw error
    }
  },

  async submit(uri: string, params: any) {
    state.loading = true
    console.debug(`Submitting Gradio job '${uri}' with params:`, params)

    try {
      const client = await this._connect()
      const result = await client.submit(uri, params)
      console.debug('Gradio job submitted successfully')
      return result
    } catch (error) {
      console.error('Failed to submit Gradio job:', error)
      throw error
    } finally {
      state.loading = false
    }
  },

  async predict(uri: string, params: any = {}) {
    state.loading = true
    console.debug(`Predicting Gradio job '${uri}' with params:`, params)

    try {
      const client = await this._connect()
      const result = await client.predict(uri, params)
      console.debug('Gradio job predicted successfully')
      return result
    } catch (error) {
      console.error('Failed to predict Gradio job:', error)
      throw error
    } finally {
      state.loading = false
    }
  }
}
