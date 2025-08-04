<script lang="ts">
  import { page } from '$app/state'
  import { Link } from '$lib/components/dsfr'
  import Footer from '$lib/components/Footer.svelte'
  import { Header } from '$lib/components/header'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'
  import ovoidPictoSrc from '@gouvfr/dsfr/dist/artwork/background/ovoid.svg'
  import errorPictoSrc from '@gouvfr/dsfr/dist/artwork/pictograms/system/technical-error.svg'

  const key = $derived(page.status === 404 ? '404' : 'unexpected')
</script>

<Header />

<main>
  <div class="fr-container">
    <div
      class="fr-my-7w fr-mt-md-12w fr-mb-md-10w fr-grid-row fr-grid-row--gutters fr-grid-row--middle fr-grid-row--center"
    >
      <div class="fr-py-0 fr-col-12 fr-col-md-6">
        <h1>{m[`errors.${key}.title`]()}</h1>
        <p class="fr-text--sm fr-mb-3w">{m[`errors.${key}.error`]({ code: page.status })}</p>
        <p class="fr-text--lead fr-mb-3w">{m[`errors.${key}.sorry`]()}</p>
        <p class="fr-text--sm fr-mb-5w">{@html sanitize(m[`errors.${key}.desc`]())}</p>

        <ul class="fr-btns-group fr-btns-group--inline-md">
          {#if key === '404'}
            <li>
              <Link button href="/" text={m['actions.home']()} />
            </li>
          {/if}
          <li>
            <Link
              button
              variant="secondary"
              href="https://adtk8x51mbw.eu.typeform.com/to/duuGRyEX"
              text={m['actions.contact']()}
            />
          </li>
        </ul>
      </div>
      <div class="fr-col-12 fr-col-md-3 fr-col-offset-md-1 fr-px-6w fr-px-md-0 fr-py-0">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="fr-responsive-img fr-artwork"
          aria-hidden="true"
          width="160"
          height="200"
          viewBox="0 0 160 200"
        >
          <use class="fr-artwork-motif" href={ovoidPictoSrc + '#artwork-motif'}></use>
          <use class="fr-artwork-background" href={ovoidPictoSrc + '#artwork-background'}></use>
          <g transform="translate(40, 60)">
            <use class="fr-artwork-decorative" href={errorPictoSrc + '#artwork-decorative'}></use>
            <use class="fr-artwork-minor" href={errorPictoSrc + '#artwork-minor'}></use>
            <use class="fr-artwork-major" href={errorPictoSrc + '#artwork-major'}></use>
          </g>
        </svg>
      </div>
    </div>
  </div>
</main>

<Footer />
