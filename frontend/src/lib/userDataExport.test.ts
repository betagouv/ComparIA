import { queryComparisons, type Comparison } from '$lib/chatService.svelte'
import { describe, expect, it } from 'vitest'
import { buildUserDataExport } from './userDataExport'

const comparison = {
  id: 'comparison-1',
  mode: 'random',
  custom_models_selection: null,
  revealed: true,
  llm_id_a: 'model-a',
  llm_id_b: 'model-b',
  system_msg_a: 'System prompt A',
  system_msg_b: 'System prompt B',
  reveal_data: {
    b64: 'internal-reveal-payload',
    chosen_llm: 'a',
    a: { llm_id: 'model-a', conso: { tokens: 42 } },
    b: { llm_id: 'model-b', conso: { tokens: 84 } }
  },
  error: 'Internal error details',
  turns: [
    {
      id: 'turn-1',
      status: 'complete',
      choice: 'a_better',
      user_msg: {
        id: 'user-message-1',
        created_at: '2026-07-21T08:00:00.000Z',
        content: 'Prompt enriched for the models',
        user_content: 'My original prompt',
        web_search_results: [
          {
            type: 'text',
            name: 'Useful source',
            url: 'https://example.test/source',
            content: 'Search result content',
            favicon: 'https://example.test/favicon.ico',
            internal_rank: 1
          }
        ],
        turn_id: 'turn-1'
      },
      a: {
        status: 'complete',
        llm_msg: {
          id: 'assistant-message-a',
          content: 'Response A',
          created_at: '2026-07-21T08:00:01.000Z',
          generation_id: 'generation-a',
          reasoning_content: 'Private reasoning A',
          tokens: 123,
          is_cached: false
        },
        keyword_annotations: ['useful', 'complete'],
        custom_annotation: 'Clear and useful'
      },
      b: {
        status: 'complete',
        llm_msg: {
          id: 'assistant-message-b',
          content: 'Response B',
          generation_id: 'generation-b',
          reasoning_content: 'Private reasoning B',
          tokens: 456,
          is_cached: true
        },
        keyword_annotations: ['superficial'],
        custom_annotation: ''
      }
    }
  ]
} as unknown as Comparison

describe('buildUserDataExport', () => {
  it('builds a stable, versioned export containing useful conversation data', () => {
    const result = buildUserDataExport(
      'personne@example.fr',
      [comparison],
      new Date('2026-07-21T09:30:00.000Z')
    )

    expect(result).toEqual({
      schema_version: 1,
      exported_at: '2026-07-21T09:30:00.000Z',
      account: { email: 'personne@example.fr' },
      conversations: [
        {
          id: 'comparison-1',
          mode: 'random',
          revealed: true,
          system_prompts: { a: 'System prompt A', b: 'System prompt B' },
          models: { a: 'model-a', b: 'model-b' },
          turns: [
            {
              id: 'turn-1',
              created_at: '2026-07-21T08:00:00.000Z',
              prompt: {
                content: 'My original prompt',
                web_search_results: [
                  {
                    name: 'Useful source',
                    url: 'https://example.test/source',
                    content: 'Search result content'
                  }
                ]
              },
              responses: {
                a: { content: 'Response A', created_at: '2026-07-21T08:00:01.000Z' },
                b: { content: 'Response B', created_at: null }
              },
              vote: {
                choice: 'a_better',
                annotations: {
                  a: { keywords: ['useful', 'complete'], comment: 'Clear and useful' },
                  b: { keywords: ['superficial'], comment: null }
                }
              }
            }
          ]
        }
      ]
    })
  })

  it('excludes technical metadata and internal errors', () => {
    const serialized = JSON.stringify(buildUserDataExport('personne@example.fr', [comparison]))

    expect(serialized).not.toContain('reasoning_content')
    expect(serialized).not.toContain('Private reasoning')
    expect(serialized).not.toContain('generation_id')
    expect(serialized).not.toContain('generation-a')
    expect(serialized).not.toContain('tokens')
    expect(serialized).not.toContain('is_cached')
    expect(serialized).not.toContain('internal-reveal-payload')
    expect(serialized).not.toContain('Internal error details')
    expect(serialized).not.toContain('favicon')
    expect(serialized).not.toContain('internal_rank')
  })

  it('does not reveal model identities before the comparison is revealed', () => {
    const hiddenComparison = {
      ...comparison,
      revealed: false,
      llm_id_a: 'hidden-model-a',
      llm_id_b: 'hidden-model-b'
    }

    const result = buildUserDataExport('personne@example.fr', [hiddenComparison])

    expect(result.conversations[0].models).toBeNull()
    expect(JSON.stringify(result)).not.toContain('hidden-model')
  })

  it('exports persisted annotations after comparisons are reloaded from the API', async () => {
    const apiComparison = {
      id: 'comparison-reloaded',
      mode: 'random',
      custom_models_selection: null,
      error: null,
      revealed: false,
      llm_id_a: 'hidden-model-a',
      llm_id_b: 'hidden-model-b',
      turns: [
        {
          id: 'turn-reloaded',
          choice: 'b_better',
          user_msg: {
            id: 'user-message-reloaded',
            content: 'Reloaded prompt',
            user_content: 'Reloaded prompt'
          },
          llm_msg_a: {
            generation_id: 'generation-a',
            content: 'Reloaded response A'
          },
          keyword_annotations_a: ['incorrect'],
          custom_annotation_a: 'Contains an error',
          llm_msg_b: {
            generation_id: 'generation-b',
            content: 'Reloaded response B'
          },
          keyword_annotations_b: ['useful', 'complete'],
          custom_annotation_b: null
        }
      ]
    }
    const reloadedComparisons = await queryComparisons(
      async () =>
        new Response(JSON.stringify([apiComparison]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        })
    )

    const result = buildUserDataExport('personne@example.fr', reloadedComparisons)

    expect(result.conversations[0].turns[0].vote.annotations).toEqual({
      a: { keywords: ['incorrect'], comment: 'Contains an error' },
      b: { keywords: ['useful', 'complete'], comment: null }
    })
    expect(result.conversations[0].models).toBeNull()
    expect(JSON.stringify(result)).not.toContain('hidden-model')
  })
})
