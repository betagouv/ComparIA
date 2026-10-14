import { describe, expect, it } from 'vitest'
import { decodeEntities, toolRequest, toolResultText, webSources } from './toolActivity'

const result = (fields: Record<string, unknown>) => ({
  type: 'tool_result' as const,
  tool_call_id: 'call-1',
  name: 'web_search',
  status: 'success' as const,
  duration_ms: 1,
  content: '',
  results: [],
  ...fields
})

describe('decodeEntities', () => {
  it('turns escaped characters back into text', () => {
    expect(decodeEntities('7 millions d&#039;euros &amp; d&#x27;aides')).toBe(
      "7 millions d'euros & d'aides"
    )
  })

  it('leaves unknown or invalid entities alone', () => {
    expect(decodeEntities('&nope; &#0; &#99999999;')).toBe('&nope; &#0; &#99999999;')
  })
})

describe('webSources', () => {
  it('keeps each http address once and decodes its title', () => {
    const sources = webSources([
      result({
        results: [
          { name: 'L&#039;aide', url: 'https://example.com/a' },
          { name: 'Again', url: 'https://example.com/a' },
          { name: 'Trap', url: 'javascript:alert(1)' }
        ]
      })
    ])

    expect(sources.map((source) => [source.name, source.url])).toEqual([
      ["L'aide", 'https://example.com/a']
    ])
  })
})

describe('toolRequest', () => {
  it('prefers the query over other arguments', () => {
    expect(
      toolRequest({
        type: 'tool_call',
        tool_call_id: 'call-1',
        name: 'search',
        arguments_json: '',
        arguments: { page: 2, query: 'logements' }
      })
    ).toBe('logements')
  })
})

describe('toolResultText', () => {
  it('reads the answer out of a JSON result', () => {
    expect(toolResultText(result({ content: '{"answer":"42"}' }))).toBe('42')
  })

  it('returns nothing for an empty result', () => {
    expect(toolResultText(result({ content: '{}' }))).toBeNull()
  })
})
