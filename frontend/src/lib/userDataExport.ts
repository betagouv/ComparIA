import type { Comparison, TurnChoice, WebSearchResults } from '$lib/chatService.svelte'

export const USER_DATA_EXPORT_SCHEMA_VERSION = 1 as const

interface ExportedSearchResult {
  name: string
  url: string
  content: string
}

interface ExportedMessage {
  content: string
  created_at: string | null
}

interface ExportedVoteAnnotations {
  keywords: string[]
  comment: string | null
}

interface ExportedTurn {
  id: string
  created_at: string | null
  prompt: {
    content: string
    web_search_results: ExportedSearchResult[]
  }
  responses: {
    a: ExportedMessage | null
    b: ExportedMessage | null
  }
  vote: {
    choice: TurnChoice | null
    annotations: {
      a: ExportedVoteAnnotations
      b: ExportedVoteAnnotations
    }
  }
}

interface ExportedConversation {
  id: string
  mode: Comparison['mode']
  revealed: boolean
  system_prompts: {
    a: string | null
    b: string | null
  }
  models: {
    a: string | null
    b: string | null
  } | null
  turns: ExportedTurn[]
}

export interface UserDataExport {
  schema_version: typeof USER_DATA_EXPORT_SCHEMA_VERSION
  exported_at: string
  account: {
    email: string
  }
  conversations: ExportedConversation[]
}

function exportSearchResults(
  results: WebSearchResults[] | null | undefined
): ExportedSearchResult[] {
  return (results ?? []).map(({ name, url, content }) => ({ name, url, content }))
}

function exportMessage(
  message: Comparison['turns'][number]['a']['llm_msg']
): ExportedMessage | null {
  if (!message) return null

  return {
    content: message.content,
    created_at: message.created_at ?? null
  }
}

function exportAnnotations(side: Comparison['turns'][number]['a']): ExportedVoteAnnotations {
  return {
    keywords: [...side.keyword_annotations],
    comment: side.custom_annotation || null
  }
}

export function buildUserDataExport(
  email: string,
  comparisons: Comparison[],
  exportedAt: Date = new Date()
): UserDataExport {
  return {
    schema_version: USER_DATA_EXPORT_SCHEMA_VERSION,
    exported_at: exportedAt.toISOString(),
    account: { email },
    conversations: comparisons.map((comparison) => ({
      id: comparison.id,
      mode: comparison.mode,
      revealed: comparison.revealed,
      system_prompts: {
        a: comparison.system_msg_a ?? null,
        b: comparison.system_msg_b ?? null
      },
      models: comparison.revealed
        ? {
            a: comparison.llm_id_a,
            b: comparison.llm_id_b
          }
        : null,
      turns: comparison.turns.map((turn) => ({
        id: turn.id,
        created_at: turn.user_msg.created_at ?? null,
        prompt: {
          content: turn.user_msg.user_content || turn.user_msg.content,
          web_search_results: exportSearchResults(turn.user_msg.web_search_results)
        },
        responses: {
          a: exportMessage(turn.a.llm_msg),
          b: exportMessage(turn.b.llm_msg)
        },
        vote: {
          choice: turn.choice,
          annotations: {
            a: exportAnnotations(turn.a),
            b: exportAnnotations(turn.b)
          }
        }
      }))
    }))
  }
}
