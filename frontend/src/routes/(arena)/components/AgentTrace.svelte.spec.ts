import { globalContext } from '$lib/testing/mockContexts'
import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import AgentTrace from './AgentTrace.svelte'

vi.mock('$env/dynamic/public', () => ({ env: {} }))
vi.mock('$lib/global.svelte', async (importOriginal) => globalContext(importOriginal))

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

describe('AgentTrace', () => {
  it('says it is calling a tool while no result yet', () => {
    render(AgentTrace, {
      props: { id: 'a', trace: [docsCall], pending: true }
    })
    const line = screen.getByRole('button', { name: /Utilisation de l'outil/ })
    expect(line.textContent).toContain('en cours')
    expect(line.textContent).toContain('Documentation SvelteKit')
  })

  it('says it is searching the web while a search runs', () => {
    render(AgentTrace, {
      props: { id: 'a', trace: [searchCall], pending: true }
    })
    expect(screen.getByRole('button', { name: /Recherche sur le web en cours/ })).toBeTruthy()
  })

  it('lists the steps in order once the model is done', () => {
    render(AgentTrace, {
      props: {
        id: 'a',
        trace: [
          { type: 'reasoning', content: 'I should check.' },
          searchCall,
          searchResult,
          docsCall,
          docsResult,
          { ...docsCall, tool_call_id: 'call-3' },
          { ...docsResult, tool_call_id: 'call-3' }
        ],
        pending: false
      }
    })

    const chips = screen.getAllByRole('button')
    expect(chips.map((chip) => chip.textContent!.replace(/\s+/g, ' ').trim())).toEqual([
      'Réflexion',
      'Réflexion terminée',
      'Recherche sur le web terminée 1',
      // Two calls in a row share a line that counts them.
      "Utilisation de l'outil « Documentation SvelteKit » terminé 2"
    ])
    const [first, ...rest] = chips
    expect(first.getAttribute('aria-expanded') === 'true').toBe(true)
    expect(rest.every((chip) => chip.getAttribute('aria-expanded') === 'false')).toBe(true)
  })

  it('keeps a tool called again later as its own step', () => {
    render(AgentTrace, {
      props: {
        id: 'a',
        trace: [
          searchCall,
          searchResult,
          docsCall,
          docsResult,

          { ...searchCall, tool_call_id: 'call-3' },
          { ...searchResult, tool_call_id: 'call-3' }
        ],
        pending: false
      }
    })

    expect(
      screen.getAllByRole('button').map((chip) => chip.textContent!.replace(/\s+/g, ' ').trim())
    ).toEqual([
      'Réflexion',
      'Recherche sur le web terminée 1',
      "Utilisation de l'outil « Documentation SvelteKit » terminé 1",
      'Recherche sur le web terminée 1'
    ])
  })

  it('opens what a tool found when its chip is pressed', async () => {
    render(AgentTrace, {
      props: {
        id: 'a',
        trace: [searchCall, searchResult, docsCall, docsResult],
        pending: false
      }
    })

    const docs = screen.getByRole('button', { name: /Documentation SvelteKit/ })
    const search = screen.getByRole('button', { name: /Recherche sur le web/ })
    expect(search.nextElementSibling).toBeNull()
    expect(docs.nextElementSibling).toBeNull()

    await fireEvent.click(docs)
    expect(docs.getAttribute('aria-expanded')).toBe('true')
    expect(docs.nextElementSibling).toBeTruthy()
    // The step names what the model asked for, not the function.
    expect(docs.nextElementSibling!.textContent).toMatch(/«\sinvalidateAll\s»/)
    await fireEvent.click(screen.getByRole('button', { name: /«\sinvalidateAll\s»/ }))
    expect(screen.queryByText('search_docs')).toBeNull()
    expect(screen.getByText(/invalidateAll is deprecated/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'https://svelte.dev/docs/kit/load' })).toBeTruthy()

    await fireEvent.click(search)
    expect(docs.getAttribute('aria-expanded')).toBe('true')
    expect(docs.nextElementSibling).toBeTruthy()
    expect(search.nextElementSibling).toBeTruthy()
    expect(screen.queryByText('web_search')).toBeNull()

    await fireEvent.click(search)
    expect(search.nextElementSibling).toBeNull()
  })

  it('shows the first sources and the rest on request', async () => {
    const results = Array.from({ length: 7 }, (_, index) => ({
      name: `Source ${index + 1}`,
      url: `https://example.com/${index + 1}`,
      favicon: null,
      content: ''
    }))
    render(AgentTrace, {
      props: { id: 'a', trace: [searchCall, { ...searchResult, results }], pending: false }
    })
    await fireEvent.click(screen.getByRole('button', { name: /Recherche sur le web/ }))
    await fireEvent.click(screen.getByRole('button', { name: /Recherche «/ }))

    expect(screen.getAllByRole('link')).toHaveLength(5)
    expect(screen.getByRole('link', { name: /Source 1/ }).textContent).toContain('example.com')
    await fireEvent.click(screen.getByRole('button', { name: 'Tout afficher' }))
    expect(screen.getAllByRole('link')).toHaveLength(7)
    await fireEvent.click(screen.getByRole('button', { name: 'Réduire' }))
    expect(screen.getAllByRole('link')).toHaveLength(5)
  })

  it('cuts a long tool answer until asked for all of it', async () => {
    const content = Array.from({ length: 12 }, (_, index) => `Ligne ${index + 1}`).join('\n')
    const { container } = render(AgentTrace, {
      props: { id: 'a', trace: [docsCall, { ...docsResult, content }], pending: false }
    })
    await fireEvent.click(screen.getByRole('button', { name: /Utilisation de l'outil/ }))
    await fireEvent.click(screen.getByRole('button', { name: /Requête «/ }))

    const text = container.querySelector('#trace-a-item-0-child-0 > div')!
    expect(text.classList.contains('max-h-36')).toBe(true)
    await fireEvent.click(screen.getByRole('button', { name: 'Tout afficher' }))
    expect(text.classList.contains('max-h-36')).toBe(false)
  })

  it('hides technical detail from visitors', async () => {
    const { container } = render(AgentTrace, {
      props: { id: 'a', trace: [searchCall, searchResult], pending: false }
    })
    await fireEvent.click(screen.getByRole('button', { name: /Recherche sur le web/ }))

    const text = container.textContent ?? ''
    expect(text).not.toContain('call-1')
    expect(text).not.toContain('321')
  })

  it('marks a tool that failed every time', async () => {
    const { container } = render(AgentTrace, {
      props: {
        id: 'a',
        trace: [docsCall, { ...docsResult, status: 'error', content: '' }],
        pending: false
      }
    })

    await fireEvent.click(
      screen.getByRole('button', {
        name: /Utilisation de l'outil «/
      })
    )
    expect(
      container.querySelector('button[aria-controls="trace-a-item-0"] .i-ri-error-warning-line')
    ).toBeTruthy()
    await fireEvent.click(
      screen.getByRole('button', {
        name: /Requête «/
      })
    )
    expect(screen.getByText("L'outil n'a pas répondu")).toBeTruthy()
  })

  it('never renders a non-http source as a link', async () => {
    render(AgentTrace, {
      props: {
        id: 'a',
        trace: [
          searchCall,
          {
            ...searchResult,
            results: [{ name: 'Piège', url: 'javascript:alert(1)', content: '', favicon: null }]
          }
        ],
        pending: false
      }
    })
    await fireEvent.click(screen.getByRole('button', { name: /Recherche sur le web/ }))

    expect(screen.queryByRole('link')).toBeNull()
  })

  it('falls back to the source domain when a favicon is unsafe', () => {
    const { container } = render(AgentTrace, {
      props: {
        id: 'a',
        trace: [
          searchCall,
          {
            ...searchResult,
            results: [{ ...searchResult.results[0], favicon: 'javascript:alert(1)' }]
          }
        ],
        pending: false
      }
    })

    expect(container.querySelector('img[src="javascript:alert(1)"]')).toBeNull()
    expect(container.querySelector('img[src="https://example.com/favicon.ico"]')).toBeTruthy()
  })
})
