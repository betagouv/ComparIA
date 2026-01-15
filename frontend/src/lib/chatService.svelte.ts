import { api } from '$lib/api'
import { m } from '$lib/i18n/messages'
import { getLocale } from '$lib/i18n/runtime'
import type { APIBotModel, BotModel } from '$lib/models'
import { parseModel } from '$lib/models'
import type { LoadingStatus } from '@gradio/statustracker'

// PROMPT
export type Mode = 'random' | 'custom' | 'big-vs-small' | 'small-models' | 'reasoning'

export interface APIModeAndPromptData {
  prompt_value: string
  mode: Mode
  custom_models_selection: string[]
}

export type ModeInfos = {
  value: Mode
  title: string
  label: string
  alt_label: string
  icon: string
  description: string
}

// CHAT

type APIMessageRole = 'system' | 'user' | 'assistant'
export type Bot = 'a' | 'b'

interface APIChatMessageMetadata<Role extends APIMessageRole = APIMessageRole> {
  bot: Role extends 'assistant' ? Bot : null
  duration: number | null
  generation_id: Role extends 'assistant' ? string : null
}

export interface APIChatMessage<Role extends APIMessageRole = APIMessageRole> {
  role: Role
  error: string | null
  metadata: APIChatMessageMetadata<Role>
  content: string
  reasoning: Role extends 'assistant' ? string | '' : null
}

export interface ChatMessage<Role extends APIMessageRole = APIMessageRole>
  extends APIChatMessage<Role> {
  index: number
  isLast: boolean
}

export type GroupedChatMessages = {
  user: ChatMessage<'user'>
  bots: [ChatMessage<'assistant'>, ChatMessage<'assistant'>]
}

// REACTIONS

// TODO use underscore everywhere ?
export const APIPositiveReactions = ['useful', 'complete', 'creative', 'clear_formatting'] as const
export const APINegativeReactions = [
  'incorrect',
  'superficial',
  'instructions_not_followed'
] as const
export type APIReactionPref =
  | (typeof APIPositiveReactions)[number]
  | (typeof APINegativeReactions)[number]
export const positiveReactions = ['useful', 'complete', 'creative', 'clear-formatting'] as const
export const negativeReactions = ['incorrect', 'superficial', 'instructions-not-followed'] as const
export type ReactionPref = (typeof positiveReactions)[number] | (typeof negativeReactions)[number]

export type ReactionKind = 'like' | 'comment'
export type APIReactionData = {
  index: number
  value: string
  liked?: boolean | null
  prefs?: ReactionPref[]
  comment?: string
}
export type OnReactionFn = (kind: ReactionKind, reaction: Required<APIReactionData>) => void

// VOTE

export interface APIVoteData {
  which_model_radio_output: 'model-a' | 'model-b' | 'both-equal'
  positive_a_output: ReactionPref[]
  positive_b_output: ReactionPref[]
  negative_a_output: ReactionPref[]
  negative_b_output: ReactionPref[]
  comments_a_output: string
  comments_b_output: string
}

interface VoteDetails {
  like: ReactionPref[]
  dislike: ReactionPref[]
  comment: string
}
export interface VoteData {
  selected?: APIVoteData['which_model_radio_output']
  a: VoteDetails
  b: VoteDetails
}

// REVEAL

type DurationUnit = 'j' | 'h' | 'min' | 's' | 'ms'

type CO2Unit = 'g' | 'mg'

type EnergyUnit = 'Wh' | 'mWh'

export interface APIRevealData {
  b64: string
  model_a: APIBotModel
  model_b: APIBotModel
  chosen_model: 'model-a' | 'model-b' | null
  model_a_energy: number
  model_a_energy_unit: EnergyUnit
  model_b_energy: number
  model_b_energy_unit: EnergyUnit
  model_a_kwh: number
  model_b_kwh: number
  model_a_co2: number
  model_a_co2_unit: CO2Unit
  model_b_co2: number
  model_b_co2_unit: CO2Unit
  model_a_tokens: number
  model_b_tokens: number
  streaming_a: number
  streaming_a_unit: DurationUnit
  streaming_b: number
  streaming_b_unit: DurationUnit
  lightbulb_a: number
  lightbulb_a_unit: DurationUnit
  lightbulb_b: number
  lightbulb_b_unit: DurationUnit
}

interface RevealModelData {
  model: BotModel
  side: 'model-a' | 'model-b'
  energy: number
  energyUnit: string
  kwh: number
  co2: number
  co2Unit: string
  tokens: number
  lightbulb: number
  lightbulbUnit: string
  streaming: number
  streamingUnit: string
}
export interface RevealData {
  selected: APIVoteData['which_model_radio_output']
  modelsData: RevealModelData[]
  shareB64Data: APIRevealData['b64']
}

// DATA

export const modeInfos: ModeInfos[] = (
  [
    { value: 'random', icon: 'dice' },
    { value: 'custom', icon: 'glass' },
    { value: 'small-models', icon: 'leaf-line' },
    { value: 'big-vs-small', icon: 'ruler' },
    { value: 'reasoning', icon: 'brain' }
  ] as const
).map((item) => ({
  ...item,
  title: m[`modes.${item.value}.title`](),
  label: m[`modes.${item.value}.label`](),
  alt_label: m[`modes.${item.value}.altLabel`](),
  description: m[`modes.${item.value}.description`]()
}))

export const arena = $state<{
  currentScreen: 'prompt' | 'chat'
  mode?: Mode
  chat: {
    step?: 1 | 2
    status: LoadingStatus['status']
    messages: APIChatMessage[]
    root: string
  }
}>({
  currentScreen: 'prompt',
  chat: {
    step: 1,
    status: 'pending',
    messages: [],
    root: '/' // FIXME or '/arene'
  }
})

// API CALLS

export async function runChatBots(args: APIModeAndPromptData) {
  arena.chat.status = 'pending'

  try {
    const job = await api.submit<APIChatMessage[]>('/add_first_text', {
      model_dropdown_scoped: args,
      locale: getLocale()
    })

    arena.currentScreen = 'chat'
    arena.mode = args.mode
    arena.chat.step = 1
    // arena.chat.status = 'streaming'

    for await (const messages of job) {
      arena.chat.status = 'generating'
      arena.chat.messages = messages
    }

    arena.chat.status = 'complete'
  } catch (error) {
    console.error('Error:', error)
    arena.chat.status = 'error'
  }

  return arena.chat.status
}

export async function askChatBots(text: string) {
  arena.chat.status = 'pending'

  try {
    const job = await api.submit<APIChatMessage[]>('/add_text', { text })
    // arena.chat.status = 'streaming'

    for await (const messages of job) {
      arena.chat.status = 'generating'
      arena.chat.messages = messages
    }

    arena.chat.status = 'complete'
  } catch (error) {
    console.error('Error:', error)
    arena.chat.status = 'error'
  }
}

export async function retryAskChatBots() {
  arena.chat.status = 'pending'

  try {
    const job = await api.submit<APIChatMessage[]>('/chatbot_retry')
    // arena.chat.status = 'streaming'

    for await (const messages of job) {
      arena.chat.status = 'generating'
      arena.chat.messages = messages
    }

    arena.chat.status = 'complete'
  } catch (error) {
    console.error('Error:', error)
    arena.chat.status = 'error'
  }
}

export async function updateReaction(kind: ReactionKind, reaction: APIReactionData) {
  const data =
    kind === 'like'
      ? {
          index: reaction.index,
          value: reaction.value,
          liked: reaction.liked,
          prefs: reaction.prefs
        }
      : {
          index: reaction.index,
          value: '',
          comment: reaction.comment
        }

  return api.predict('/chatbot_react', {
    // pass complete raw messages array
    chatbot: arena.chat.messages,
    reaction_json: data
  })
}

export async function postVoteGetReveal(vote: Required<VoteData>) {
  const data = {
    which_model_radio_output: vote.selected,
    positive_a_output: vote.a.like,
    positive_b_output: vote.b.like,
    negative_a_output: vote.a.dislike,
    negative_b_output: vote.b.dislike,
    comments_a_output: vote.a.comment,
    comments_b_output: vote.b.comment
  } satisfies APIVoteData
  return api.predict<APIRevealData>('/chatbot_vote', data).then(parseAPIRevealData)
}

function parseAPIRevealData(data: APIRevealData): RevealData {
  return {
    selected: data.chosen_model ?? 'both-equal',
    modelsData: (['a', 'b'] as const).map((model) => ({
      model: parseModel(data[`model_${model}`]),
      side: `model-${model}`,
      energy: data[`model_${model}_energy`],
      energyUnit: data[`model_${model}_energy_unit`],
      kwh: data[`model_${model}_kwh`],
      co2: data[`model_${model}_co2`],
      co2Unit: data[`model_${model}_co2_unit`],
      tokens: data[`model_${model}_tokens`],
      lightbulb: data[`lightbulb_${model}`],
      lightbulbUnit: data[`lightbulb_${model}_unit`],
      streaming: data[`streaming_${model}`],
      streamingUnit: data[`streaming_${model}_unit`]
    })),
    shareB64Data: data.b64
  }
}

export async function getReveal(): Promise<RevealData> {
  return api.predict<APIRevealData>('/reveal').then(parseAPIRevealData)
}
