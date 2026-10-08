import { fireEvent, render, screen } from '@testing-library/svelte'
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
  it('shares the comparison row equally without letting content set the column width', () => {
    const { container } = render(
      MessageBot,
      props({
        role: 'assistant',
        generation_id: 'generation-a',
        content: 'Final answer.',
        agent_trace: []
      })
    )

    const column = container.firstElementChild

    expect(column?.classList.contains('md:flex-1')).toBe(true)
    expect(column?.classList.contains('md:min-w-0')).toBe(true)
  })

  it('interposes intermediate content and tool calls before the final answer', () => {
    render(
      MessageBot,
      props({
        role: 'assistant',
        generation_id: 'generation-a',
        content: 'Answer informed by the search.',
        agent_stop_reason: 'completed',
        agent_trace: [
          {
            type: 'intermediate_content',
            content: 'I will verify this first.'
          },
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
          },
          {
            type: 'intermediate_content',
            content: 'I found a lead and will verify it.'
          },
          {
            type: 'tool_call',
            tool_call_id: 'call-2',
            name: 'legal_lookup',
            label: 'Jurisprudence',
            arguments_json: '{"subject":"current information"}',
            arguments: { subject: 'current information' }
          },
          {
            type: 'tool_result',
            tool_call_id: 'call-2',
            name: 'legal_lookup',
            status: 'success',
            duration_ms: 8,
            content: 'Verification complete.',
            results: []
          }
        ]
      })
    )

    const preamble = screen.getByText('I will verify this first.')
    const firstTool = screen.getByRole('button', { name: /Recherche web/ })
    const middle = screen.getByText('I found a lead and will verify it.')
    const secondTool = screen.getByRole('button', { name: /Jurisprudence/ })
    const answer = screen.getByText('Answer informed by the search.')

    expect(preamble.compareDocumentPosition(firstTool) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    )
    expect(firstTool.compareDocumentPosition(middle) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    )
    expect(middle.compareDocumentPosition(secondTool) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    )
    expect(secondTool.compareDocumentPosition(answer) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    )
  })

  it('does not add a redundant status when a model does not use an offered tool', () => {
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

    expect(screen.queryByText('Aucun outil utilisé')).toBeNull()
  })

  it('keeps reasoning and tool calls that follow each other in one row of chips', () => {
    const { container } = render(
      MessageBot,
      props({
        role: 'assistant',
        generation_id: 'generation-a',
        content: 'Final answer.',
        agent_trace: [
          { type: 'reasoning', content: 'I should look it up.' },
          {
            type: 'tool_call',
            tool_call_id: 'call-1',
            name: 'search_docs',
            label: 'Documentation SvelteKit',
            arguments_json: '{"query":"load"}',
            arguments: { query: 'load' }
          },
          { type: 'reasoning', content: 'That answers it.' }
        ]
      })
    )

    expect(container.querySelectorAll('.agent-activity__panel')).toHaveLength(1)
    expect(
      screen.getAllByRole('button', { expanded: false }).map((chip) => chip.textContent?.trim())
    ).toEqual(['Réflexion', 'Documentation SvelteKit'])
  })

  it('shows the live step instead of the loading line while the model works', () => {
    const message = {
      role: 'assistant',
      generation_id: 'generation-a',
      content: '',
      agent_trace: [
        {
          type: 'tool_call',
          tool_call_id: 'call-1',
          name: 'search_docs',
          label: 'Documentation SvelteKit',
          arguments_json: '{"query":"load"}',
          arguments: { query: 'load' }
        }
      ]
    }
    const { container } = render(MessageBot, {
      ...props(message),
      turnSide: { ...turnSide(message), status: 'generating' }
    } as unknown as ComponentProps<typeof MessageBot>)

    expect(container.querySelector('.agent-activity__live')).toBeTruthy()
    expect(container.querySelector('[role="status"]')).toBeNull()
  })

  it('shows reasoning as a chip like the tools', async () => {
    const { container } = render(
      MessageBot,
      props({
        role: 'assistant',
        generation_id: 'generation-a',
        content: 'Final answer.',
        agent_trace: [
          {
            type: 'reasoning',
            content: 'I should verify this carefully.'
          }
        ]
      })
    )

    await fireEvent.click(screen.getByRole('button', { name: 'Réflexion' }))
    expect(screen.getByText('I should verify this carefully.')).toBeTruthy()
    expect(container.querySelector('.fr-accordion')).toBeNull()
  })
})
