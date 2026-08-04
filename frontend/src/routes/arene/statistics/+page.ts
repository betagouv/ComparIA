import { api } from '$lib/fastapi-client'

export type StatisticsSummary = {
  questions_count: number
  votes_count: number
  daily_conversations: Array<{ date: string; count: number }>
}

export async function load({ fetch }) {
  const statistics = await api.request<StatisticsSummary>('/statistics/summary', { fetch })
  return { statistics }
}
