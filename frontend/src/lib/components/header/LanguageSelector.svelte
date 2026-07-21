<script lang="ts">
  import { page } from '$app/state'
  import { getAuthContext } from '$lib/auth.svelte'
  import Dropdown from '$components/Dropdown.svelte'
  import { getLocales, type LocaleOption } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale, setLocale } from '$lib/i18n/runtime'
  import type { SvelteHTMLElements } from 'svelte/elements'
  import { SvelteURL } from 'svelte/reactivity'

  let { id, ...props }: { id: string } & SvelteHTMLElements['nav'] = $props()

  const auth = getAuthContext()
  const locales = $derived(getLocales(auth.config.enabled_locales))
  const currentLocale = getLocale()

  function onLocaleSelect(locale: LocaleOption) {
    if (page.url.host !== locale.host) {
      const url = new SvelteURL(window.location.href)
      url.host = locale.host
      url.search = `locale=${locale.code}`
      window.location.href = url.href
    } else {
      setLocale(locale.code)
    }
  }
</script>

<nav {...props} class={['language-selector fr-translate fr-nav whitespace-nowrap', props.class]}>
  <Dropdown
    id="dropdown-{id}"
    label={locales.find((locale) => locale.code === currentLocale)?.short ??
      currentLocale.toUpperCase()}
    title={m['actions.selectLanguage']()}
    buttonClass="fr-translate__btn rounded-sm!"
    closeOnSelect
  >
    <ul class="fr-sidemenu__list">
      {#each locales as locale (locale.code)}
        <li class="fr-sidemenu__item">
          <button
            class="fr-sidemenu__link py-2! font-normal! font-sm!"
            lang={locale.code}
            aria-current={locale.code == currentLocale}
            onclick={() => onLocaleSelect(locale)}
          >
            {locale.long}
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
