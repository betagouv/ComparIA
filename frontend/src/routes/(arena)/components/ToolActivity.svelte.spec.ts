import { render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import ToolActivity from './ToolActivity.svelte'

vi.mock('$env/dynamic/public', () => ({ env: {} }))

const tools = [
  { key: 'web_search', label: 'Recherche web', description: 'Chercher sur le web' }
]

const searchCall = {
  type: 'tool_call' as const,
  tool_call_id: 'call-1',
  name: 'web_search',
  arguments_json: '{"query":"prix immobilier Nantes"}',
  arguments: { query: 'prix immobilier Nantes' }
}

const searchResult = {
  type: 'tool_result' as const,
  tool_call_id: 'call-1',
  name: 'web_search',
  status: 'success' as const,
  duration_ms: 321,
  content: '{"results":[]}',
  results: [
    {
      type: 'text',
      name: 'DVF Nantes',
      url: 'https://example.com/dvf',
      content: 'Prix au mètre carré.'
    }
  ]
}

describe('ToolActivity', () => {
  it('names the tool in French and shows the query the model wrote', () => {
    render(ToolActivity, {
      props: { id: 'a', events: [searchCall, searchResult], tools, finished: true }
    })

    expect(screen.getByText('Recherche web')).toBeTruthy()
    expect(screen.getByText(/prix immobilier Nantes/)).toBeTruthy()
    expect(screen.getByText(/1 source/)).toBeTruthy()
  })

  it('hides technical detail from visitors', () => {
    const { container } = render(ToolActivity, {
      props: { id: 'a', events: [searchCall, searchResult], tools, finished: true }
    })

    const text = container.textContent ?? ''
    expect(text).not.toContain('call-1')
    expect(text).not.toContain('321')
    expect(text).not.toContain('arguments_json')
  })

  it('says the model used no tool, phrased as a choice', () => {
    render(ToolActivity, { props: { id: 'a', events: [], tools, finished: true } })

    expect(screen.getByText('Aucun outil utilisé')).toBeTruthy()
  })

  it('stays quiet while the model is still answering', () => {
    const { container } = render(ToolActivity, {
      props: { id: 'a', events: [], tools, finished: false }
    })

    expect(container.textContent?.trim()).toBe('')
  })

  it('shows the request while the call is still running', () => {
    render(ToolActivity, {
      props: { id: 'a', events: [searchCall], tools, finished: false }
    })

    expect(screen.getByText('Recherche web')).toBeTruthy()
    expect(screen.getByText(/Recherche en cours/)).toBeTruthy()
  })

  it('never renders a non-http source as a link', () => {
    render(ToolActivity, {
      props: {
        id: 'a',
        events: [
          searchCall,
          {
            ...searchResult,
            results: [
              {
                type: 'text',
                name: 'Piège',
                url: 'javascript:alert(1)',
                content: ''
              }
            ]
          }
        ],
        tools,
        finished: true
      }
    })

    expect(screen.queryByRole('link')).toBeNull()
  })
})
