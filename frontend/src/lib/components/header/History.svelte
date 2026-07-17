<script lang="ts">
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import AILogo from '$components/AILogo.svelte'
  import { Link } from '$components/dsfr'
  import { getComparisonsContext } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { getModelsContext } from '$lib/models'
  import type { SvelteHTMLElements } from 'svelte/elements'

  const {
    mode = 'desktop',
    expanded,
    ...props
  }: { mode?: 'desktop' | 'mobile'; expanded: boolean } & SvelteHTMLElements['nav'] = $props()

  const comparisons = getComparisonsContext()
  const { models } = getModelsContext()
</script>

{#snippet logo(llm_id?: string, chosen?: boolean)}
  <span
    aria-hidden="true"
    class={[
      'p-1 b-1 rounded-full',
      { 'b-primary bg-[#E8EDFF]': chosen, 'b-[#DDD]': !!llm_id, 'b-primary b-dashed': !llm_id }
    ]}
  >
    {#if llm_id}
      {@const logo = models.find((llm) => llm.id === llm_id)!.lab.logo}
      <AILogo {logo} size="sm" alt="" class="block" />
    {:else}
      <span class="i-ri-question-mark block h-[14px] w-[14px]"></span>
    {/if}
  </span>
{/snippet}

{#if comparisons.length}
  <div class={['gap-2 lg:min-h-0 flex flex-col', { 'lg:hidden': !expanded }]}>
    <div class="px-4">
      <p class="text-sm! mb-0! text-black font-bold">
        {m['auth.discussions.title']()}
      </p>
    </div>
    <nav {...props} class={['comparison-history lg:overflow-y-auto', props.class]}>
      <ul class="fr-sidemenu__list">
        {#each comparisons as comp (comp.id)}
          {@const href = resolve(`/arene/${comp.id}`)}
          {@const current = page.url.pathname === href ? 'page' : undefined}
          <li class={['fr-sidemenu__item', { 'before:content-none!': mode === 'mobile' }]}>
            <Link
              {href}
              aria-current={current}
              class="fr-sidemenu__link py-1! font-normal! text-sm!"
              aria-controls={mode === 'mobile' ? 'fr-modal-menu' : undefined}
            >
              <span class="max-w-[145px] shrink truncate">{comp.turns[0]?.user_msg.content}</span>
              <span class="gap-1 ms-auto flex items-center">
                {@render logo(
                  comp.reveal_data?.a.llm_id,
                  comp.reveal_data?.chosen_llm === 'a'
                )}/{@render logo(comp.reveal_data?.b.llm_id, comp.reveal_data?.chosen_llm === 'b')}
              </span>
            </Link>
          </li>
        {/each}
      </ul>
    </nav>
  </div>
{/if}

<style lang="postcss">
  .comparison-history {
    :global(.fr-sidemenu__link[aria-current]:not([aria-current='false'])) {
      --text-active-blue-france: var(--blue-france-main-525);
      --border-active-blue-france: var(--blue-france-main-525);

      &::before {
        width: 4px;
        top: 0;
        bottom: 0;
      }
    }
  }
</style>
