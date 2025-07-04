export type Mode = 'random' | 'custom' | 'big-vs-small' | 'small-models' | 'reasoning'
export type ModeIcon = 'glass' | 'ruler' | 'brain' | 'dice' | 'leaf'
export type ModeInfos = {
  value: Mode
  title: string
  label: string
  alt_label: string
  icon: ModeIcon
  description: string
}

export type State = {
  currentScreen: 'initial' | 'chatbots'
  step?: 1 | 2
  mode?: Mode
  votes?: { count: number; objective: number; ratio: number }
  loading: boolean
}

export const state = $state<State>({
  currentScreen: 'initial',
  loading: false
})

export const modeInfos: ModeInfos[] = [
  {
    value: 'random',
    title: 'Mode Aléatoire',
    label: 'Aléatoire',
    alt_label: 'Modèles aléatoires',
    description: 'Deux modèles choisis au hasard parmi toute la liste',
    icon: 'dice'
  },
  {
    value: 'custom',
    title: 'Mode Sélection',
    label: 'Sélection manuelle',
    alt_label: 'Sélection manuelle',
    description: 'Reconnaîtrez-vous les deux modèles que vous avez choisis ?',
    icon: 'glass'
  },
  {
    value: 'small-models',
    title: 'Mode Frugal',
    label: 'Frugal',
    alt_label: 'Modèles frugaux',
    description: 'Deux modèles tirés au hasard parmi ceux de plus petite taille',
    icon: 'leaf'
  },
  {
    value: 'big-vs-small',
    title: 'Mode David contre Goliath',
    label: 'David contre Goliath',
    alt_label: 'David contre Goliath',
    description: 'Un petit modèle contre un grand, les deux tirés au hasard',
    icon: 'ruler'
  },
  {
    value: 'reasoning',
    title: 'Mode Raisonnement',
    label: 'Raisonnement',
    alt_label: 'Modèles avec raisonnement',
    description: 'Deux modèles tirés au hasard parmi ceux optimisés pour des tâches complexes',
    icon: 'brain'
  }
] as const
