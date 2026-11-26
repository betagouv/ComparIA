import type { ToolPublic } from '$lib/generated/backend'
import { describe, expect, it } from 'vitest'
import { _createToolsContext } from './global.svelte'

const webSearch: ToolPublic = { key: 'web_search', label: 'Recherche web', enabled: true }
const datagouv: ToolPublic = { key: 'datagouv', label: 'Données publiques', enabled: false }

describe('tools context', () => {
  it('picks the tools behind stored keys, in their order', () => {
    const tools = _createToolsContext(() => [webSearch, datagouv])

    expect(tools.pick(['datagouv', 'web_search']).map((tool) => tool.key)).toEqual([
      'datagouv',
      'web_search'
    ])
  })

  it('leaves out keys it does not know rather than failing', () => {
    // The arena loads the tools list with an empty fallback when /tools fails.
    expect(_createToolsContext(() => []).pick(['web_search'])).toEqual([])
    expect(_createToolsContext(() => [webSearch]).pick(['gone', 'web_search'])).toHaveLength(1)
  })
})
