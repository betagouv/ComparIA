import { render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import MessageBot from './MessageBot.svelte'

vi.mock('$env/dynamic/public', () => ({ env: {} }))

describe('MessageBot', () => {
  it('shows completed web searches before the answer they informed', () => {
    render(MessageBot, {
      id: 'message-a',
      prompt: 'Find current information.',
      bot: 'a',
      choice: null,
      onVoteAnnotate: () => undefined,
      turnSide: {
        status: 'complete',
        keyword_annotations: [],
        custom_annotation: '',
        llm_msg: {
          role: 'assistant',
          generation_id: 'generation-a',
          content: 'Answer informed by the search.',
          web_search_results: [
            {
              type: 'text',
              name: 'Current source',
              url: 'https://example.com/current',
              content: 'Current information'
            }
          ]
        }
      }
    })

    const searchStep = screen.getByRole('button', {
      name: 'Résultats de recherche Web associés.'
    })
    const answer = screen.getByText('Answer informed by the search.')

    expect(searchStep.compareDocumentPosition(answer) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    )
  })
})
