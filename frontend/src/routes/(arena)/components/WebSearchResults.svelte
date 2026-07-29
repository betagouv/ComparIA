<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import type { WebSearchResults } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { isSafeWebSource } from '$lib/utils/commons'

  export type WebSearchResultsProps = {
    id: string
    results: WebSearchResults[]
  }

  let { id, results }: WebSearchResultsProps = $props()
  const safeResults = $derived(results.filter((result) => isSafeWebSource(result.url)))
</script>

{#if safeResults.length > 0}
  <section class="fr-accordion p-3 bg-white cg-border my-3 before:shadow-none!">
    <h3 class="fr-accordion__title">
      <button
        type="button"
        class="fr-accordion__btn text-black! p-0! flex! min-h-auto! bg-transparent!"
        aria-expanded="false"
        aria-controls={id}
      >
        <Icon icon="i-ri-global-line" size="sm" class="text-primary me-1" />
        <span class="text-[12px]">{m['chatbot.webSearch.label']()}</span>
      </button>
    </h3>
    <div {id} class="fr-collapse m-0! p-0!">
      <ul class="mt-2! text-sm m-0! p-0! xl:grid-cols-2 md:max-h-[150px] grid max-h-[100px]">
        {#each safeResults as search, i (`${search.url}-${i}`)}
          <li class="gap-3 flex items-center">
            {#if search.favicon && isSafeWebSource(search.favicon)}
              <img aria-hidden="true" alt="" src={search.favicon} class="h-[14px] w-[14px]" />
            {/if}
            <span>
              <Link
                href={search.url}
                text={search.name || search.url}
                class="text-black! lh-tight! text-[12px]!"
              />
            </span>
          </li>
        {/each}
      </ul>
    </div>
  </section>
{/if}
