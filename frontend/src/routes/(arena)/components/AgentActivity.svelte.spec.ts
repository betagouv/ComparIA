import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import type { AgentTraceToolCall, AgentTraceToolResult } from '$lib/generated/backend'
import AgentActivity from './AgentActivity.svelte'
import type { ActivityStep } from './toolActivity'

vi.mock('$env/dynamic/public', () => ({ env: {} }))

const searchCall = {
  type: 'tool_call' as const,
  tool_call_id: 'call-1',
  name: 'web_search',
  label: 'Recherche web',
  tool: 'web_search',
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
      name: 'DVF Nantes',
      url: 'https://example.com/dvf',
      favicon: 'https://cdn.example.com/dvf.ico',
      content: 'Prix au mètre carré.'
    }
  ]
}

const docsCall = {
  type: 'tool_call' as const,
  tool_call_id: 'call-2',
  name: 'search_docs',
  label: 'Documentation SvelteKit',
  tool: 'sveltekit_docs',
  arguments_json: '{"query":"invalidateAll"}',
  arguments: { query: 'invalidateAll' }
}

const docsResult = {
  type: 'tool_result' as const,
  tool_call_id: 'call-2',
  name: 'search_docs',
  status: 'success' as const,
  duration_ms: 12,
  content: 'invalidateAll is deprecated. https://svelte.dev/docs/kit/load.',
  results: []
}

const tool = (call: AgentTraceToolCall, result: AgentTraceToolResult | null): ActivityStep => ({
  type: 'tool',
  call,
  result
})

describe('AgentActivity', () => {
  it('names the tool on one moving line while it runs', () => {
    const { container } = render(AgentActivity, {
      props: { id: 'a', steps: [tool(docsCall, null)], active: true }
    })

    const line = container.querySelector('.agent-activity__live')!
    expect(line.textContent).toContain('Consulte')
    expect(line.querySelector('strong')!.textContent).toBe('Documentation SvelteKit')
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('says it is searching the web while a search runs', () => {
    const { container } = render(AgentActivity, {
      props: { id: 'a', steps: [tool(searchCall, null)], active: true }
    })

    expect(container.querySelector('.agent-activity__live')!.textContent).toContain(
      'Cherche sur le web'
    )
  })

  it('lists the steps in order once the model is done', () => {
    render(AgentActivity, {
      props: {
        id: 'a',
        steps: [
          { type: 'reasoning', content: 'I should check.' },
          tool(searchCall, searchResult),
          tool(docsCall, docsResult),
          tool({ ...docsCall, tool_call_id: 'call-3' }, { ...docsResult, tool_call_id: 'call-3' })
        ],
        active: false
      }
    })

    const chips = screen.getAllByRole('button')
    expect(chips.map((chip) => chip.textContent!.replace(/\s+/g, ' ').trim())).toEqual([
      'Réflexion',
      'Recherche web « prix immobilier Nantes » 1 1 source',
      'Documentation SvelteKit'
    ])
    expect(chips.every((chip) => chip.getAttribute('aria-expanded') === 'false')).toBe(true)
  })

  it('keeps a tool called again later as its own step', () => {
    render(AgentActivity, {
      props: {
        id: 'a',
        steps: [
          tool(searchCall, searchResult),
          tool(docsCall, docsResult),
          tool(
            { ...searchCall, tool_call_id: 'call-3' },
            { ...searchResult, tool_call_id: 'call-3' }
          )
        ],
        active: false
      }
    })

    expect(
      screen.getAllByRole('button').map((chip) => chip.textContent!.replace(/\s+/g, ' ').trim())
    ).toEqual([
      'Recherche web « prix immobilier Nantes » 1 1 source',
      'Documentation SvelteKit « invalidateAll »',
      'Recherche web « prix immobilier Nantes » 1 1 source'
    ])
  })

  it('opens what a tool found when its chip is pressed', async () => {
    const { container } = render(AgentActivity, {
      props: {
        id: 'a',
        steps: [tool(searchCall, searchResult), tool(docsCall, docsResult)],
        active: false
      }
    })

    const searchPanel = container.querySelector<HTMLElement>('#a-panel-0')!
    const docsPanel = container.querySelector<HTMLElement>('#a-panel-1')!
    expect(searchPanel.hidden).toBe(true)
    expect(docsPanel.hidden).toBe(true)

    const docs = screen.getByRole('button', { name: /Documentation SvelteKit/ })
    await fireEvent.click(docs)
    expect(docs.getAttribute('aria-expanded')).toBe('true')
    expect(docsPanel.hidden).toBe(false)
    // The step names what the model asked for, not the function.
    expect(docs.textContent).toMatch(/«\sinvalidateAll\s»/)
    expect(screen.queryByText('search_docs')).toBeNull()
    expect(screen.getByText(/invalidateAll is deprecated/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'https://svelte.dev/docs/kit/load' })).toBeTruthy()

    await fireEvent.click(screen.getByRole('button', { name: /Recherche web/ }))
    expect(docs.getAttribute('aria-expanded')).toBe('false')
    expect(docsPanel.hidden).toBe(true)
    expect(searchPanel.hidden).toBe(false)
    expect(screen.queryByText('web_search')).toBeNull()

    await fireEvent.click(screen.getByRole('button', { name: /Recherche web/ }))
    expect(searchPanel.hidden).toBe(true)
  })

  it('shows the first sources and the rest on request', async () => {
    const results = Array.from({ length: 7 }, (_, index) => ({
      name: `Source ${index + 1}`,
      url: `https://example.com/${index + 1}`,
      favicon: null,
      content: ''
    }))
    render(AgentActivity, {
      props: { id: 'a', steps: [tool(searchCall, { ...searchResult, results })], active: false }
    })
    await fireEvent.click(screen.getByRole('button'))

    expect(screen.getAllByRole('link')).toHaveLength(5)
    expect(screen.getByRole('link', { name: /Source 1/ }).textContent).toContain('example.com')
    await fireEvent.click(screen.getByRole('button', { name: 'Toutes les sources (7)' }))
    expect(screen.getAllByRole('link')).toHaveLength(7)
    await fireEvent.click(screen.getByRole('button', { name: 'Réduire' }))
    expect(screen.getAllByRole('link')).toHaveLength(5)
  })

  it('cuts a long tool answer until asked for all of it', async () => {
    const content = Array.from({ length: 12 }, (_, index) => `Ligne ${index + 1}`).join('\n')
    const { container } = render(AgentActivity, {
      props: { id: 'a', steps: [tool(docsCall, { ...docsResult, content })], active: false }
    })
    await fireEvent.click(screen.getByRole('button'))

    const text = container.querySelector('.agent-activity__text')!
    expect(text.classList.contains('agent-activity__text--cut')).toBe(true)
    await fireEvent.click(screen.getByRole('button', { name: 'Tout afficher' }))
    expect(text.classList.contains('agent-activity__text--cut')).toBe(false)
  })

  it('hides technical detail from visitors', async () => {
    const { container } = render(AgentActivity, {
      props: { id: 'a', steps: [tool(searchCall, searchResult)], active: false }
    })
    await fireEvent.click(screen.getByRole('button'))

    const text = container.textContent ?? ''
    expect(text).not.toContain('call-1')
    expect(text).not.toContain('321')
  })

  it('marks a tool that failed every time', async () => {
    const { container } = render(AgentActivity, {
      props: {
        id: 'a',
        steps: [tool(docsCall, { ...docsResult, status: 'error', content: '' })],
        active: false
      }
    })

    expect(container.querySelector('.agent-activity__dot .i-ri-error-warning-line')).toBeTruthy()
    await fireEvent.click(screen.getByRole('button'))
    expect(screen.getByText("L'outil n'a pas répondu")).toBeTruthy()
  })

  it('never renders a non-http source as a link', async () => {
    render(AgentActivity, {
      props: {
        id: 'a',
        steps: [
          tool(searchCall, {
            ...searchResult,
            results: [{ name: 'Piège', url: 'javascript:alert(1)', content: '', favicon: null }]
          })
        ],
        active: false
      }
    })
    await fireEvent.click(screen.getByRole('button'))

    expect(screen.queryByRole('link')).toBeNull()
  })

  it('falls back to the source domain when a favicon is unsafe', () => {
    const { container } = render(AgentActivity, {
      props: {
        id: 'a',
        steps: [
          tool(searchCall, {
            ...searchResult,
            results: [{ ...searchResult.results[0], favicon: 'javascript:alert(1)' }]
          })
        ],
        active: false
      }
    })

    expect(container.querySelector('img[src="javascript:alert(1)"]')).toBeNull()
    expect(container.querySelector('img[src="https://example.com/favicon.ico"]')).toBeTruthy()
  })
})
