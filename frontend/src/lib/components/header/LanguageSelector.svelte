<script lang="ts">
  import { LOCALES, changeLocale, global } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'

  let { id }: { id: string } = $props()
</script>

<!-- FIXME see 'global.locale' comment -->
{#if global.locale}
  <nav class="fr-translate fr-nav">
    <div class="fr-nav__item">
      <button
        aria-controls={id}
        aria-expanded="false"
        title={m['actions.selectLanguage']()}
        type="button"
        class="fr-translate__btn fr-btn fr-btn--tertiary-no-outline before:content-none!"
      >
        <img
          src={`/flags/${global.locale}.png`}
          aria-hidden="true"
          alt=""
          class="me-2 max-w-[30px] rounded-md"
        />
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
{/if}
