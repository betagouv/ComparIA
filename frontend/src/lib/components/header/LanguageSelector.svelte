<script lang="ts">
  import { page } from '$app/state'
  import { Button } from '$components/dsfr'
  import { LOCALES, type LocaleOption } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale, setLocale } from '$lib/i18n/runtime'
  import { SvelteURL } from 'svelte/reactivity'

  let { id }: { id: string } = $props()

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

<nav class="fr-translate fr-nav">
  <div class="fr-nav__item">
    <Button
      aria-controls={id}
      aria-expanded="false"
      title={m['actions.selectLanguage']()}
      variant="tertiary-no-outline"
      native
      class="fr-translate__btn before:content-none!"
    >
      <img
        src={`/flags/${currentLocale}.png`}
        aria-hidden="true"
        alt=""
        class="me-2 rounded-md max-w-[30px]"
      />
      {LOCALES.find((locale) => locale.code === currentLocale)!.short}
    </Button>

    <div class="fr-collapse fr-translate__menu fr-menu" {id}>
      <ul class="fr-menu__list">
        {#each LOCALES as locale (locale.code)}
          <li>
            <button
              class="fr-translate__language fr-nav__link"
              lang={locale.code}
              aria-current={locale.code == currentLocale}
              onclick={() => onLocaleSelect(locale)}
            >
              {locale.long}
            </button>
          </li>
        {/each}
      </ul>
    </div>
  </div>
</nav>
