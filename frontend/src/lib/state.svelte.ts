export type State = {
  currentScreen: 'initial' | 'chatbots'
  step?: number,
  loading: boolean
}

export const state = $state<State>({
  currentScreen: 'initial',
  loading: false,
})
