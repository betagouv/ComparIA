import { render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import AgentTrace from './AgentTrace.svelte'

vi.mock('$env/dynamic/public', () => ({ env: {} }))

describe('AgentTrace', () => {
  it('shows every execution event in order and keeps raw details collapsible', () => {
    render(AgentTrace, {
      props: {
        id: 'trace-a',
        prompt: 'Quelle est la météo actuelle à Paris ?',
        events: [
          { type: 'reasoning', content: 'Je dois vérifier une information actuelle.' },
          { type: 'intermediate_content', content: 'Je vais consulter le web.' },
          {
            type: 'tool_call',
            tool_call_id: 'call-1',
            name: 'linkup_web_search',
            arguments_json: '{"query":"météo actuelle Paris"}',
            arguments: { query: 'météo actuelle Paris' }
          },
          {
            type: 'tool_result',
            tool_call_id: 'call-1',
            name: 'linkup_web_search',
            status: 'success',
            duration_ms: 321,
            content: '{"results":[{"name":"Météo Paris"}]}',
            results: [
              {
                type: 'text',
                name: 'Météo Paris',
                url: 'https://example.com/meteo',
                content: 'Conditions actuelles.'
              }
            ]
          }
        ]
      }
    })

    const traceButton = screen.getByRole('button', { name: 'Voir la trace d’exécution' })
    expect(traceButton.getAttribute('aria-expanded')).toBe('false')
    expect(screen.getByText('Quelle est la météo actuelle à Paris ?')).toBeTruthy()
    expect(screen.getByText('météo actuelle Paris')).toBeTruthy()
    expect(screen.getAllByText('Afficher les détails techniques')).toHaveLength(2)
    expect(screen.getByText('{"query":"météo actuelle Paris"}')).toBeTruthy()

    const request = screen.getByRole('heading', { name: 'Requête utilisateur' })
    const toolCall = screen.getByRole('heading', { name: /Appel de l’outil/ })
    const toolResult = screen.getByRole('heading', { name: /Réponse de l’outil/ })
    const intermediate = screen.getByRole('heading', { name: 'Message intermédiaire du modèle' })

    expect(request.compareDocumentPosition(intermediate) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    )
    expect(intermediate.compareDocumentPosition(toolCall) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    )
    expect(toolCall.compareDocumentPosition(toolResult) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    )
  })

  it('does not turn unsafe result URLs into links', () => {
    render(AgentTrace, {
      props: {
        id: 'trace-unsafe',
        prompt: 'Test',
        events: [
          {
            type: 'tool_result',
            tool_call_id: 'call-unsafe',
            name: 'linkup_web_search',
            status: 'success',
            duration_ms: 10,
            content: 'raw',
            results: [
              {
                type: 'text',
                name: 'Unsafe source',
                url: 'javascript:alert(1)',
                content: 'Untrusted'
              }
            ]
          }
        ]
      }
    })

    expect(screen.getByText('Unsafe source')).toBeTruthy()
    expect(screen.queryByRole('link', { name: 'Unsafe source' })).toBeNull()
  })
})
