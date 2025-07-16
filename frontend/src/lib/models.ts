import { api } from '$lib/api'

export type Sizes = 'XS' | 'S' | 'M' | 'L' | 'XL'

export interface APIBotModel {
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
  friendly_size: Sizes
  simple_name: string
  organisation: string
  params: number
  total_params?: number
  distribution: 'open-weights' | 'api-only'
  icon_path: string
  release_date?: string | null
  fully_open_source?: boolean
  license: string
  conditions: 'free' | 'copyleft' | 'restricted'
  required_ram: number
  url?: string
  description: string
  excerpt: string
  quantization?: 'q4' | 'q8'
}

export async function getModels() {
  return api.predict<APIBotModel[]>('/enter_arena')
}
