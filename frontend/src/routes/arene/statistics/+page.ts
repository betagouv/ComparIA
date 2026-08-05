import { api } from '$lib/fastapi-client'

export type StatisticsPeriod = '7d' | '30d' | '90d' | 'all'
export type StatisticsSummary = {
  period: StatisticsPeriod
  granularity: 'day' | 'week' | 'month'
  prompts_count: number
  conversations_count: number
  models_count: number
  activity: Array<{ date: string; prompts: number; conversations: number }>
}

export async function load({ fetch, url }) {
  const requestedPeriod = url.searchParams.get('period')
  const period: StatisticsPeriod = ['7d', '30d', '90d', 'all'].includes(requestedPeriod ?? '')
    ? (requestedPeriod as StatisticsPeriod)
    : '30d'
  const statistics = await api.request<StatisticsSummary>(`/statistics/summary?period=${period}`, {
    fetch
  })
  return { statistics }
}
