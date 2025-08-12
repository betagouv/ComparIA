import { getContext, setContext } from 'svelte'

export const LICENSES = [
  'MIT',
  'Apache 2.0',
  'Gemma',
  'Llama 3 Community',
  'Llama 3.1',
  'Llama 3.3',
  'Llama 4',
  'Jamba Open Model',
  'CC-BY-NC-4.0',
  'propriétaire Gemini',
  'propriétaire Mistral',
  'propriétaire xAI',
  'propriétaire Liquid',
  'propriétaire OpenAI',
  'propriétaire Anthropic',
  'Mistral AI Non-Production'
] as const

export type Sizes = 'XS' | 'S' | 'M' | 'L' | 'XL'

type License = (typeof LICENSES)[number]

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
  license: License
  conditions: 'free' | 'copyleft' | 'restricted'
  required_ram: number
  url?: string
  description: string
  excerpt: string
  quantization?: 'q4' | 'q8'
}

export const licenseAttrs: Record<string, { warningCommercial?: true; prohibitCommercial?: true }> =
  {
    // Utilisation commerciale
    // Modification autorisée
    // Attribution requise
    // "MIT": {"commercial": true, "can_modify": true, "attribution": true},
    // "Apache 2.0": {"commercial": true, "can_modify": true, "attribution": true},
    // "Gemma": {"copyleft": true},
    'Llama 3 Community': { warningCommercial: true },
    'Llama 3.1': { warningCommercial: true },
    'Llama 3.3': { warningCommercial: true },
    'Jamba Open Model': { warningCommercial: true },
    'CC-BY-NC-4.0': { prohibitCommercial: true },
    'Mistral AI Non-Production': { prohibitCommercial: true },
    'Mistral AI Research': { prohibitCommercial: true }
  }

export function setModelsContext(models: APIBotModel[]) {
  setContext('models', models)
}

export function getModelsContext() {
  return getContext<APIBotModel[]>('models')
}

export function isAvailableLicense(license: string): license is License {
  return (LICENSES as ReadonlyArray<string>).includes(license)
}