import type { ModeAndPromptData } from '$lib/utils-customdropdown'

export type State = {
  currentScreen: 'initial' | 'chatbots'
  step?: 1 | 2
  mode?: ModeAndPromptData['mode']
  votes?: { count: number; objective: number; ratio: number }
  loading: boolean
}

export const state = $state<State>({
  currentScreen: 'initial',
  loading: false
})
