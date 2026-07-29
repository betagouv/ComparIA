<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import type { LLMMessageCreate } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import { isSafeWebSource } from '$lib/utils/commons'

  type AgentTraceEvent = NonNullable<LLMMessageCreate['agent_trace']>[number]

  export type ToolActivityProps = {
    id: string
    events: AgentTraceEvent[]
    /** False while the model is still answering: nothing is settled yet. */
    finished: boolean
  }

  let { id, events, finished }: ToolActivityProps = $props()

  // One entry per call, its result attached once it lands. Built by walking the
  // trace in order so the interface shows what the model asked for while the
  // call is still running.
  const calls = $derived.by(() => {
    const byId = new Map<
      string,
      {
        label: string
        query: string | null
        ok: boolean
        sources: { url: string; name: string }[] | null
      }
    >()
    for (const event of events) {
      if (event.type === 'tool_call') {
        const query = typeof event.arguments?.query === 'string' ? event.arguments.query : null
        byId.set(event.tool_call_id, {
          label: event.label || event.name,
          query,
          ok: false,
          sources: null
        })
      } else if (event.type === 'tool_result') {
        const call = byId.get(event.tool_call_id)
        if (call) {
          call.ok = event.status === 'success'
          call.sources = (event.results ?? [])
            .filter((result) => !!result.url && isSafeWebSource(result.url))
            .map((result) => ({
              url: result.url as string,
              name: result.name || (result.url as string)
            }))
        }
      }
    }
    return [...byId.values()]
  })
</script>

{#if calls.length > 0}
  <ul class="mb-4 ps-0! list-none">
    {#each calls as call, index (index)}
      <li class="mb-2">
        <p class="mb-1! text-sm">
          <Icon icon="i-ri-search-line" size="sm" class="text-primary me-1" />
          <span class="font-medium">{call.label}</span>
          {#if call.query}
            <span class="text-[--text-mention-grey]">&nbsp;«&nbsp;{call.query}&nbsp;»</span>
          {/if}
        </p>

        {#if call.sources === null}
          <p class="mb-0! ms-5 text-sm text-[--text-mention-grey]">
            {m['chatbot.tools.running']()}
          </p>
        {:else if call.sources.length > 0}
          <details class="ms-5">
            <summary class="text-sm cursor-pointer text-[--text-mention-grey]">
              {m['chatbot.tools.sources']({ count: call.sources.length })}
            </summary>
            <ul class="mt-1! mb-0! ps-4! text-sm">
              {#each call.sources as source, sourceIndex (`${source.url}-${sourceIndex}`)}
                <li class="mb-1">
                  <Link href={source.url} text={source.name} class="text-[13px]!" />
                </li>
              {/each}
            </ul>
          </details>
        {:else}
          <p class="mb-0! ms-5 text-sm text-[--text-mention-grey]">
            {call.ok ? m['chatbot.tools.done']() : m['chatbot.tools.noResult']()}
          </p>
        {/if}
      </li>
    {/each}
  </ul>
{:else if finished}
  <p {id} class="mb-4 text-sm text-[--text-mention-grey]">
    <Icon icon="i-ri-checkbox-blank-circle-line" size="sm" class="me-1" />
    {m['chatbot.tools.none']()}
  </p>
{/if}
