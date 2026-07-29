import { render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import ToolActivity from './ToolActivity.svelte'

vi.mock('$env/dynamic/public', () => ({ env: {} }))

const searchCall = {
  type: 'tool_call' as const,
  tool_call_id: 'call-1',
  name: 'web_search',
  label: 'Recherche web',
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
      type: 'text' as const,
      name: 'DVF Nantes',
      url: 'https://example.com/dvf',
      favicon: 'https://cdn.example.com/dvf.ico',
      content: 'Prix au mètre carré.'
    }
  ]
}

describe('ToolActivity', () => {
  it('shows a web search as a compact expandable row', () => {
    const { container } = render(ToolActivity, {
      props: { id: 'a', call: searchCall, result: searchResult, finished: true }
    })

    expect(screen.getByText('Recherche web')).toBeTruthy()
    expect(screen.getByText(/prix immobilier Nantes/)).toBeTruthy()
    expect(screen.getByText('1 résultat')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'DVF Nantes' })).toBeTruthy()
    expect(container.querySelector('details.tool-activity-card')).toBeTruthy()
    expect(container.querySelector('summary')).toBeTruthy()
    expect(container.querySelector('.i-ri-global-line')).toBeTruthy()
    expect(container.querySelector('img[src="https://cdn.example.com/dvf.ico"]')).toBeTruthy()
    expect(container.querySelector('.tool-activity-content')).toBeTruthy()
    expect(container.querySelector('.bg-white')).toBeTruthy()
    expect(container.querySelector('.bg-\\[--background-contrast-grey\\]')).toBeNull()
    expect(container.querySelector('details.w-full')).toBeTruthy()
    expect(container.querySelector('summary.min-h-12')).toBeNull()
  })

  it('hides technical detail from visitors', () => {
    const { container } = render(ToolActivity, {
      props: { id: 'a', call: searchCall, result: searchResult, finished: true }
    })

    const text = container.textContent ?? ''
    expect(text).not.toContain('call-1')
    expect(text).not.toContain('321')
    expect(text).not.toContain('arguments_json')
  })

  it('shows the request while the call is still running', () => {
    render(ToolActivity, {
      props: { id: 'a', call: searchCall, result: null, finished: false }
    })

    expect(screen.getByText('Recherche web')).toBeTruthy()
    expect(screen.getByText(/Recherche en cours/)).toBeTruthy()
    expect(screen.getByText(/prix immobilier Nantes/)).toBeTruthy()
  })

  it('never renders a non-http source as a link', () => {
    render(ToolActivity, {
      props: {
        id: 'a',
        call: searchCall,
        result: {
          ...searchResult,
          results: [
            {
              type: 'text' as const,
              name: 'Piège',
              url: 'javascript:alert(1)',
              content: ''
            }
          ]
        },
        finished: true
      }
    })

    expect(screen.queryByRole('link')).toBeNull()
  })

  it('falls back to the source domain when a favicon is unsafe', () => {
    const { container } = render(ToolActivity, {
      props: {
        id: 'a',
        call: searchCall,
        result: {
          ...searchResult,
          results: [{ ...searchResult.results[0], favicon: 'javascript:alert(1)' }]
        },
        finished: true
      }
    })

    expect(container.querySelector('img[src="javascript:alert(1)"]')).toBeNull()
    expect(container.querySelector('img[src="https://example.com/favicon.ico"]')).toBeTruthy()
  })

  it('renders a generic tool request and textual result without requiring sources', () => {
    render(ToolActivity, {
      props: {
        id: 'generic',
        call: {
          type: 'tool_call',
          tool_call_id: 'call-2',
          name: 'legal_lookup',
          label: 'Jurisprudence',
          arguments_json: '{"subject":"droit du travail"}',
          arguments: { subject: 'droit du travail' }
        },
        result: {
          type: 'tool_result',
          tool_call_id: 'call-2',
          name: 'legal_lookup',
          status: 'success',
          duration_ms: 12,
          content: 'Deux décisions pertinentes ont été trouvées.',
          results: []
        },
        finished: true
      }
    })

    expect(screen.getByText('Jurisprudence')).toBeTruthy()
    expect(screen.getByText(/droit du travail/)).toBeTruthy()
    expect(screen.getByText('Deux décisions pertinentes ont été trouvées.')).toBeTruthy()
  })
})
