<script lang="ts">
  import Dropdown from '$components/Dropdown.svelte'
  import { getLocalesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let { id, ...props }: { id: string } & SvelteHTMLElements['nav'] = $props()

  const locales = getLocalesContext()
</script>

<nav
  {...props}
  aria-label={m['a11y.languageNav']()}
  class={['language-selector fr-translate fr-nav whitespace-nowrap', props.class]}
>
  <Dropdown
    id="dropdown-{id}"
    label={locales.getLabel(locales.current, 'short')}
    title={m['actions.selectLanguage']()}
    buttonClass="fr-translate__btn rounded-sm!"
    closeOnSelect
  >
    <ul class="fr-sidemenu__list">
      {#each locales.enabledOptions as locale (locale.value)}
        <li class="fr-sidemenu__item">
          <button
            class="fr-sidemenu__link py-2! font-normal! font-sm!"
            lang={locale.value}
            aria-current={locale.value == locales.current}
            onclick={() => (locales.current = locale.value)}
          >
            {locale.label}
          </button>
        </li>
      {/each}
    </ul>
  </Dropdown>
</nav>

<style lang="postcss">
  .language-selector {
    :global(.fr-sidemenu__link) {
      outline-offset: -2px;

      &[aria-current]:not([aria-current='false']) {
        --text-active-blue-france: var(--blue-france-main-525);
        --border-active-blue-france: var(--blue-france-main-525);

        &::before {
          width: 4px;
          top: 0;
          bottom: 0;
        }
      }
    }
  }
</style>
