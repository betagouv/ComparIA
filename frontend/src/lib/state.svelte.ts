import { api } from '$lib/api'
import { m } from '$lib/i18n/messages.js'

export type Mode = 'random' | 'custom' | 'big-vs-small' | 'small-models' | 'reasoning'
export type ModeInfos = {
  value: Mode
  title: string
  label: string
  alt_label: string
  icon: string
  description: string
}

export type State = {
  currentScreen: 'initial' | 'chatbots'
  step?: 1 | 2
  mode?: Mode
  votes?: { count: number; objective: number }
  loading: boolean
}

export const state = $state<State>({
  currentScreen: 'initial',
  loading: false
})

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

export function getVotes() {
  return api.get<State['votes']>('/counter').then((data) => {
    state.votes = data
  })
}
