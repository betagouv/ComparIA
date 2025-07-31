import { api } from '$lib/api'

export type State = {
  loading: boolean
  votes?: { count: number; objective: number }
}

export const infos = $state<State>({
  loading: false
})

export function getVotes() {
  return api.get<State['votes']>('/counter').then((data) => {
    infos.votes = data
  })
}
