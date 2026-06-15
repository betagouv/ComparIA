<script lang="ts">
  import { page } from '$app/state'
  import { Button } from '$components/dsfr'
  import { INSTANCES, LOCALES, type Instance, type LocaleOption } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale, setLocale } from '$lib/i18n/runtime'

  let { id }: { id: string } = $props()

  const currentLocale = getLocale()
  const currentHost = page.url.host

  const localeOptions = LOCALES.filter((l) => l.host === currentHost)

  function onLocaleSelect(locale: LocaleOption) {
    setLocale(locale.code)
  }

  function onInstanceSelect(instance: Instance) {
    if (instance.host === currentHost) return
    window.location.href = `${window.location.protocol}//${instance.host}`
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
      <p class="fr-text--xs fr-mb-0 px-4 pt-2 text-[var(--text-mention-grey)] uppercase">
        {m['actions.selectLocale']()}
      </p>
      <ul class="fr-menu__list">
        {#each localeOptions as locale (locale.code)}
          <li>
            <button
              class="fr-translate__language fr-nav__link"
              lang={locale.code}
              aria-current={locale.code === currentLocale}
              onclick={() => onLocaleSelect(locale)}
            >
              {locale.long}
            </button>
          </li>
        {/each}
      </ul>
      <hr class="my-1 mx-4 border-[var(--border-default-grey)]" />
      <p class="fr-text--xs fr-mb-0 px-4 pt-1 text-[var(--text-mention-grey)] uppercase">
        {m['actions.selectInstance']()}
      </p>
      <ul class="fr-menu__list">
        {#each INSTANCES as instance (instance.host)}
          <li>
            <button
              class="fr-translate__language fr-nav__link"
              aria-current={instance.host === currentHost}
              onclick={() => onInstanceSelect(instance)}
            >
              {instance.label}
            </button>
          </li>
        {/each}
      </ul>
    </div>
  </div>
</nav>
