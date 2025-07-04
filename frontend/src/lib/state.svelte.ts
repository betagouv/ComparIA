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

export const modeInfos = {
  custom: [
    'Mode Sélection',
    'Reconnaîtrez-vous les deux modèles que vous avez choisis ?',
    'glass.svg'
  ],
  'big-vs-small': [
    'Mode David contre Goliath',
    'Un petit modèle contre un grand, les deux tirés au hasard',
    'ruler.svg'
  ],
  reasoning: [
    'Mode Raisonnement',
    'Deux modèles tirés au hasard parmi ceux optimisés pour des tâches complexes',
    'brain.svg'
  ],
  random: ['Mode Aléatoire', 'Deux modèles choisis au hasard parmi toute la liste', 'dice.svg'],
  'small-models': [
    'Mode Frugal',
    'Deux modèles tirés au hasard parmi ceux de plus petite taille',
    'leaf.svg'
  ]
}
