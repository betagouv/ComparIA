<script lang="ts">
  import { LOCALES, changeLocale, global } from '$lib/global.svelte'

  let { id }: { id: string } = $props()
</script>

<nav class="fr-translate fr-nav">
  <div class="fr-nav__item">
    <button
      aria-controls={id}
      aria-expanded="false"
      title="Sélectionner une langue"
      type="button"
      class="fr-translate__btn fr-btn fr-btn--tertiary"
    >
      {LOCALES.find((locale) => locale.code === global.locale)!.short}
    </button>
    <div class="fr-collapse fr-translate__menu fr-menu" {id}>
      <ul class="fr-menu__list">
        {#each LOCALES as locale}
          <li>
            <button
              class="fr-translate__language fr-nav__link"
              lang={locale.code}
              aria-current={locale.code == global.locale}
              onclick={() => changeLocale(locale.code)}
            >
              {locale.long}
            </button>
          </li>
        {/each}
      </ul>
    </div>
  </div>
</nav>
