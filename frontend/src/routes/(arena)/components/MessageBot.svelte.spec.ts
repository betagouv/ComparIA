import { render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import MessageBot from './MessageBot.svelte'
import type { ComponentProps } from 'svelte'

vi.mock('$env/dynamic/public', () => ({ env: {} }))

const turnSide = (llm_msg: Record<string, unknown>) => ({
  status: 'complete' as const,
  keyword_annotations: [],
  custom_annotation: '',
  llm_msg
})

const props = (llm_msg: Record<string, unknown>) =>
  ({
    id: 'message-a',
    prompt: 'Find current information.',
    bot: 'a' as const,
    choice: null,
    onVoteAnnotate: () => undefined,
    turnSide: turnSide(llm_msg)
  }) as unknown as ComponentProps<typeof MessageBot>

describe('MessageBot', () => {
  it('shows what the model searched before the answer it informed', () => {
    render(
      MessageBot,
      props({
        role: 'assistant',
        generation_id: 'generation-a',
        content: 'Answer informed by the search.',
        agent_stop_reason: 'completed',
        agent_trace: [
          {
            type: 'tool_call',
            tool_call_id: 'call-1',
            name: 'web_search',
            label: 'Recherche web',
            arguments_json: '{"query":"current information"}',
            arguments: { query: 'current information' }
          },
          {
            type: 'tool_result',
            tool_call_id: 'call-1',
            name: 'web_search',
            status: 'success',
            duration_ms: 12,
            content: '{}',
            results: [
              {
                type: 'text',
                name: 'Current source',
                url: 'https://example.com/current',
                content: 'Current information'
              }
            ]
          }
        ]
      })
    )

    const activity = screen.getByText('Recherche web')
    const answer = screen.getByText('Answer informed by the search.')

    expect(activity.compareDocumentPosition(answer) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    )
  })

  it('says a model offered tools chose not to use them', () => {
    render(
      MessageBot,
      props({
        role: 'assistant',
        generation_id: 'generation-a',
        content: 'Answered from memory.',
        agent_stop_reason: 'completed',
        agent_trace: []
      })
    )

    expect(screen.getByText('Aucun outil utilisé')).toBeTruthy()
  })

  it('stays silent when no tool was ever offered', () => {
    render(
      MessageBot,
      props({
        role: 'assistant',
        generation_id: 'generation-a',
        content: 'Plain answer.'
      })
    )

    expect(screen.queryByText('Aucun outil utilisé')).toBeNull()
  })
})
