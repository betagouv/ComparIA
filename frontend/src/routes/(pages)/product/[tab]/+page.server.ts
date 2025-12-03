import { error } from '@sveltejs/kit'

export function load({ params }) {
  const TABS = ['community', 'comparator', 'problem', 'history', 'faq', 'partners'] as const
  type TabsId = (typeof TABS)[number]

  if (!TABS.includes(params.tab as TabsId)) {
    error(404)
  }

  return {
    tab: params.tab as TabsId
  }
}
