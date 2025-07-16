import { api } from '$lib/api'
import { state, type Mode } from '$lib/state.svelte'
import type { LoadingStatus } from '@gradio/statustracker'
import type { APIBotModel, Sizes } from '$lib/models'

// PROMPT

export interface APIModeAndPromptData {
  prompt_value: string
  mode: Mode
  custom_models_selection: string[]
}

// MESSAGES

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

type DurationUnit = 'j' | 'h' | 'min' | 's'

export interface APIRevealData {
  b64: string
  model_a: APIBotModel
  model_b: APIBotModel
  chosen_model: 'model-a' | 'model-b' | null
  model_a_kwh: number
  model_b_kwh: number
  model_a_co2: number
  model_b_co2: number
  size_desc: Record<Sizes, string>
  license_desc: Record<string, string>
  license_attrs: Partial<
    Record<string, { warning_commercial: boolean; prohibit_commercial: boolean }>
  >
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
  model: APIBotModel
  side: 'model-a' | 'model-b'
  kwh: number
  co2: number
  tokens: number
  lightbulb: number
  lightbulbUnit: string
  streaming: number
  streamingUnit: string
}
export interface RevealData {
  selected: APIVoteData['which_model_radio_output']
  modelsData: RevealModelData[]
  sizeDesc: APIRevealData['size_desc']
  licenseDesc: APIRevealData['license_desc']
  licenseAttrs: APIRevealData['license_attrs']
  shareB64Data: APIRevealData['b64']
}

// DATA

export const chatbot = $state<{
  status: LoadingStatus['status']
  messages: APIChatMessage[]
  root: string
}>({
  status: 'pending',
  messages: [],
  root: '/' // FIXME or '/arene'
})

// API CALLS

export async function runChatBots(args: APIModeAndPromptData) {
  chatbot.status = 'pending'

  try {
    const job = await api.submit<APIChatMessage[]>('/add_first_text', {
      model_dropdown_scoped: args
    })

    state.currentScreen = 'chatbots'
    state.mode = args.mode
    // FIXME get api data
    state.votes = { count: 1000, objective: 2000, ratio: 50 }
    state.step = 1
    // chatbot.status = 'streaming'

    for await (const messages of job) {
      chatbot.status = 'generating'
      chatbot.messages = messages
    }

    chatbot.status = 'complete'
  } catch (error) {
    console.error('Error:', error)
    chatbot.status = 'error'
  }

  return chatbot.status
}

export async function askChatBots(text: string) {
  chatbot.status = 'pending'

  try {
    const job = await api.submit<APIChatMessage[]>('/add_text', { text })
    // chatbot.status = 'streaming'

    for await (const messages of job) {
      chatbot.status = 'generating'
      chatbot.messages = messages
    }

    chatbot.status = 'complete'
  } catch (error) {
    console.error('Error:', error)
    chatbot.status = 'error'
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
    chatbot: chatbot.messages,
    reaction_json: data
  })
}

export async function postVoteGetReveal(vote: Required<VoteData>) {
  const data = {
    which_model_radio_output: vote.selected,
    positive_a_output: vote.a.like,
    positive_b_output: vote.b.like,
    negative_a_output: vote.a.like,
    negative_b_output: vote.b.dislike,
    comments_a_output: vote.a.comment,
    comments_b_output: vote.b.comment
  } satisfies APIVoteData
  return api.predict<APIRevealData>('/chatbot_vote', data).then(parseAPIRevealData)
}

function parseAPIRevealData(data: APIRevealData): RevealData {
  console.log('d', data)
  return {
    selected: data.chosen_model ?? 'both-equal',
    modelsData: (['a', 'b'] as const).map((model) => ({
      model: data[`model_${model}`],
      side: `model-${model}`,
      kwh: data[`model_${model}_kwh`],
      co2: data[`model_${model}_co2`] * 1000,
      tokens: data[`model_${model}_tokens`],
      lightbulb: data[`lightbulb_${model}`],
      lightbulbUnit: data[`lightbulb_${model}_unit`],
      streaming: data[`streaming_${model}`],
      streamingUnit: data[`streaming_${model}_unit`]
    })),
    sizeDesc: data.size_desc,
    licenseDesc: data.license_desc,
    licenseAttrs: data.license_attrs,
    shareB64Data: data.b64
  }
}
export async function getReveal(): Promise<RevealData> {
  return api.predict<APIRevealData>('/reveal').then(parseAPIRevealData)
}
