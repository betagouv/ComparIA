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
  custom: {
    title: 'Mode Sélection',
    description: 'Reconnaîtrez-vous les deux modèles que vous avez choisis ?',
    icon: 'glass'
  },
  'big-vs-small': {
    title: 'Mode David contre Goliath',
    description: 'Un petit modèle contre un grand, les deux tirés au hasard',
    icon: 'ruler'
  },
  reasoning: {
    title: 'Mode Raisonnement',
    description: 'Deux modèles tirés au hasard parmi ceux optimisés pour des tâches complexes',
    icon: 'brain'
  },
  random: {
    title: 'Mode Aléatoire',
    description: 'Deux modèles choisis au hasard parmi toute la liste',
    icon: 'dice'
  },
  'small-models': {
    title: 'Mode Frugal',
    description: 'Deux modèles tirés au hasard parmi ceux de plus petite taille',
    icon: 'leaf'
  }
} as const
