<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import type { AgentTraceEvent } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import { isSafeWebSource } from './WebSearchResults.svelte'

  export type AgentTraceProps = {
    id: string
    prompt: string
    events: AgentTraceEvent[]
  }

  let { id, prompt, events }: AgentTraceProps = $props()
</script>

<section class="fr-accordion p-3 bg-white cg-border my-3 before:shadow-none!">
  <h4 class="fr-accordion__title">
    <button
      type="button"
      class="fr-accordion__btn text-black! p-0! flex! min-h-auto! bg-transparent!"
      aria-expanded="false"
      aria-controls={id}
    >
      <Icon icon="i-ri-route-line" size="sm" class="text-primary me-1" />
      <span class="text-[12px]">{m['chatbot.agentTrace.label']()}</span>
    </button>
  </h4>

  <div {id} class="fr-collapse m-0! p-0!">
    <ol class="mt-4! mb-0! ps-6! text-sm">
      <li class="mb-4">
        <h5 class="mb-1! text-sm!">{m['chatbot.agentTrace.request']()}</h5>
        <p class="mb-0! break-words whitespace-pre-wrap">{prompt}</p>
      </li>

      {#each events as event, index (`${event.type}-${index}`)}
        <li class="mb-4">
          {#if event.type === 'reasoning'}
            <h5 class="mb-1! text-sm!">{m['chatbot.agentTrace.reasoning']()}</h5>
            <p class="mb-0! break-words whitespace-pre-wrap">{event.content}</p>
          {:else if event.type === 'intermediate_content'}
            <h5 class="mb-1! text-sm!">{m['chatbot.agentTrace.intermediate']()}</h5>
            <p class="mb-0! break-words whitespace-pre-wrap">{event.content}</p>
          {:else if event.type === 'tool_call'}
            <h5 class="mb-1! text-sm!">
              {m['chatbot.agentTrace.toolCall']()} <code>{event.name}</code>
            </h5>
            {#if typeof event.arguments?.query === 'string'}
              <p class="mb-2!">
                <strong>{m['chatbot.agentTrace.query']()}</strong>
                <span class="break-words whitespace-pre-wrap">{event.arguments.query}</span>
              </p>
            {/if}
            <details>
              <summary class="cursor-pointer">{m['chatbot.agentTrace.technicalDetails']()}</summary>
              <pre
                class="mt-2! mb-0! p-2 text-xs bg-alt-blue-france overflow-auto break-words whitespace-pre-wrap">{event.arguments_json}</pre>
            </details>
          {:else if event.type === 'tool_result'}
            <h5 class="mb-1! text-sm!">
              {m['chatbot.agentTrace.toolResult']()} <code>{event.name}</code>
            </h5>
            <p class="mb-2!">
              {m[`chatbot.agentTrace.status.${event.status}`]()} · {event.duration_ms} ms ·
              {event.results.length}
              {m['chatbot.agentTrace.sources']()}
            </p>
            {#if event.results.length}
              <ul class="mb-2! ps-4!">
                {#each event.results as result, resultIndex (`${result.url}-${resultIndex}`)}
                  <li class="mb-2">
                    {#if isSafeWebSource(result.url)}
                      <Link href={result.url} text={result.name || result.url} />
                    {:else}
                      <span>{result.name || result.url}</span>
                    {/if}
                    {#if result.content}
                      <p class="mb-0! text-xs break-words whitespace-pre-wrap">{result.content}</p>
                    {/if}
                  </li>
                {/each}
              </ul>
            {/if}
            <details>
              <summary class="cursor-pointer">{m['chatbot.agentTrace.technicalDetails']()}</summary>
              <pre
                class="mt-2! mb-0! p-2 max-h-80 text-xs bg-alt-blue-france overflow-auto break-words whitespace-pre-wrap">{event.content}</pre>
            </details>
          {/if}
        </li>
      {/each}
    </ol>
  </div>
</section>
