<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import type { UserMessage } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'

  export type MessageUserProps = {
    id: string
    message: UserMessage
  }

  let { id, message }: MessageUserProps = $props()

  // Search results come from the provider, so a javascript: or data: URL must
  // never reach an href or an img src.
  function safeUrl(url: string | undefined, schemes: string[]): string | undefined {
    if (!url) return undefined
    return schemes.some((scheme) => url.toLowerCase().startsWith(scheme)) ? url : undefined
  }
</script>

<div class="message-user md:ms-auto md:max-w-3/5 rounded-2xl px-5 py-3 bg-light-info">
  <Markdown message={message.user_content} kind="user" />

  {#if message.web_search_results}
    <section class="fr-accordion p-3 bg-white cg-border mt-3 before:shadow-none!">
      <h2 class="fr-accordion__title">
        <button
          type="button"
          class="fr-accordion__btn text-black! p-0! flex! min-h-auto! bg-transparent!"
          aria-expanded="false"
          aria-controls={id}
        >
          <Icon icon="i-ri-global-line" size="sm" class="text-primary me-1" />
          <span class="text-[12px]">{m['chatbot.webSearch.label']()}</span>
        </button>
      </h2>
      <div {id} class="fr-collapse m-0! p-0!">
        <ul class="mt-2! text-sm m-0! p-0! xl:grid-cols-2 md:max-h-[150px] grid max-h-[100px]">
          {#each message.web_search_results as search, i (i)}
            {@const favicon = safeUrl(search.favicon, ['http://', 'https://', 'data:image/'])}
            {@const url = safeUrl(search.url, ['http://', 'https://'])}
            <li class="gap-3 flex items-center">
              {#if favicon}
                <img aria-hidden="true" alt="" src={favicon} class="h-[14px] w-[14px]" />
              {/if}
              <span>
                {#if url}
                  <Link href={url} text={search.name} class="text-black! lh-tight! text-[12px]!" />
                {:else}
                  <span class="lh-tight! text-[12px]">{search.name}</span>
                {/if}
              </span>
            </li>
          {/each}
        </ul>
      </div>
    </section>
  {/if}
</div>

<style>
  .message-user :global(p:last-of-type) {
    margin: 0;
  }
</style>
