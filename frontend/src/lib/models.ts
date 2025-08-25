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
  params: number
  active_params?: number
  friendly_size: Sizes
  arch: string
  reasoning: boolean | 'hybrid'
  quantization?: 'q4' | 'q8'
  required_ram: number
  url?: string // FIXME required?
  // conditions: 'free' | 'copyleft' | 'restricted'
}
export type BotModel = ReturnType<typeof parseModel>

export function parseModel(model: APIBotModel) {
  return {
    ...model,
    desc: m[`generated.models.${model.simple_name}.desc`](),
    sizeDesc: m[`generated.models.${model.simple_name}.size_desc`](),
    fyi: m[`generated.models.${model.simple_name}.fyi`](),
    licenseInfos:
      model.license === 'proprietary'
        ? {
            desc: m[`generated.licenses.proprio.${model.organisation}.license_desc`](),
            reuseSpecificities:
              m[`generated.licenses.proprio.${model.organisation}.reuse_specificities`](),
            commercialUseSpecificities:
              m[`generated.licenses.proprio.${model.organisation}.commercial_use_specificities`]()
          }
        : {
            desc: m[`generated.licenses.os.${model.license}.license_desc`](),
            reuseSpecificities: m[`generated.licenses.os.${model.license}.reuse_specificities`](),
            commercialUseSpecificities:
              m[`generated.licenses.os.${model.license}.commercial_use_specificities`]()
          },
    badges: {
      license: {
        'fully-open-source': {
          id: `model-os-${model.id}`,
          variant: 'green' as const,
          text: m['models.licenses.type.openSource'](),
          tooltip: m['models.openWeight.tooltips.openSource']()
        },
        'open-weights': {
          id: `model-ow-${model.id}`,
          variant: 'yellow' as const,
          text: m['models.licenses.type.semiOpen'](),
          tooltip: m['models.openWeight.tooltips.openWeight']()
        },
        'api-only': {
          id: `model-proprietary-${model.id}`,
          variant: 'orange' as const,
          text: m['models.licenses.type.proprietary']()
        }
      }[model.distribution],
      releaseDate: model.release_date
        ? ({
            variant: '' as const,
            text: m['models.release']({ date: model.release_date })
          } as const)
        : null,
      licenseName: { variant: '' as const, text: model.license },
      size: {
        id: `model-parameters-${model.id}`,
        variant: 'info' as const,
        text:
          model.distribution === 'open-weights'
            ? m['models.parameters']({ number: model.params })
            : m['models.size.estimated']({ size: model.friendly_size }),
        tooltip:
          model.distribution === 'api-only' ? m['models.openWeight.tooltips.params']() : undefined
      },
      arch: {
        // FIXME need description and label for 'maybe-*'
        id: `model-arch-${model.id}`,
        variant: 'yellow' as const,
        text: model.arch
        // tooltip: ''
      },
      reasoning: model.reasoning ? ({ variant: '', text: 'Modèle de raisonnement' } as const) : null
    }
  }
}

export function setModelsContext(models: APIBotModel[]) {
  setContext(
    'models',
    models.map((model) => parseModel(model))
  )
}

export function getModelsContext() {
  return getContext<BotModel[]>('models')
}
