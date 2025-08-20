import { getContext, setContext } from 'svelte'
import { m } from './i18n/messages'

export const SIZES = ['XS', 'S', 'M', 'L', 'XL'] as const
export const LICENSES = [
  'proprietary',
  'CC-BY-NC-4.0',
  'Apache 2.0',
  'Llama 3.1',
  'Llama 4',
  'Mistral AI Research License',
  'Llama 3.3',
  'MIT',
  'Gemma'
] as const
export const ORGANISATIONS = [
  'Meta',
  'DeepSeek',
  'Cohere',
  'xAI',
  'Microsoft',
  'Google',
  'Alibaba',
  'Moonshot AI',
  'Nvidia',
  'OpenAI',
  'Mistral AI',
  'Amazon',
  'Anthropic',
  'Zhipu',
  'Nous'
] as const
export const MODELS = [
  'Llama 3.1 405B',
  'Llama 3.3 70B',
  'Llama 3.1 8B',
  'Llama 4 Scout',
  'Llama Maverick',
  'DeepSeek R1',
  'DeepSeek R1 Llama 70B',
  'DeepSeek V3',
  'Aya Expanse 32B',
  'Command A',
  'Command R',
  'Grok 3 Mini',
  'Phi-4',
  'Gemini 2.5 Flash',
  'Gemma 3n 4B',
  'Gemma 3 4B',
  'Gemma 3 12B',
  'Gemma 3 27B',
  'qwq 32B',
  'Qwen 2.5 Coder 32B',
  'Qwen 3 32B',
  'Qwen 3 30B A3B',
  'Qwen 2.5 max 0125',
  'Nemotron Llama 3.1 70B',
  'GPT OSS-120B',
  'GPT OSS-20B',
  'GPT 5',
  'GPT 5 Mini',
  'GPT 5 Nano',
  'GPT 4.1 Nano',
  'GPT-4.1 Mini',
  'o4 mini',
  'Mistral Large 2',
  'Mistral Saba',
  'Mistral Small 3.2',
  'Magistral Medium',
  'Mistral Medium 2506',
  'Magistral Small',
  'Ministral',
  'Claude 3.7 Sonnet',
  'Claude 4 Sonnet',
  'Hermes 3 405B'
] as const

export type Sizes = (typeof SIZES)[number]
export type License = (typeof LICENSES)[number]
export type Organisation = (typeof ORGANISATIONS)[number]
export type Model = (typeof MODELS)[number]

export interface APIBotModel {
  id: string
  simple_name: Model
  organisation: Organisation
  icon_path: string
  distribution: 'api-only' | 'open-weights' | 'fully-open-source'
  license: License
  reuse: boolean
  commercial_use: boolean | null
  release_date: string
  params: number | null
  active_params: number | null
  friendly_size: Sizes
  arch: string
  reasoning: boolean | 'hybrid'
  url: string | null // FIXME required?
  // conditions: 'free' | 'copyleft' | 'restricted'
  // required_ram: number
  // quantization?: 'q4' | 'q8'
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
