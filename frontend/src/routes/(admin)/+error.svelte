<script lang="ts">
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Link } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'
  import ovoidPictoSrc from '@gouvfr/dsfr/dist/artwork/background/ovoid.svg'
  import errorPictoSrc from '@gouvfr/dsfr/dist/artwork/pictograms/system/technical-error.svg'

  const key = $derived(page.status === 404 ? '404' : 'unexpected')
</script>

<div class="flex h-full items-center">
  <div class="gap-10 md:flex-row p-4 lg:p-10 my-auto flex grow flex-col">
    <div class="max-w-[600px]">
      <h1>{m[`errors.${key}.title`]()}</h1>
      <p class="fr-text--sm fr-mb-3w">{m[`errors.${key}.error`]({ code: page.status })}</p>
      <p class="fr-text--lead fr-mb-3w">{m[`errors.${key}.sorry`]()}</p>
      <p class="fr-text--sm fr-mb-5w">{@html sanitize(m[`errors.${key}.desc`]())}</p>

      {#if key === '404'}
        <ul class="fr-btns-group fr-btns-group--inline-md">
          <li>
            <Link button href={resolve('/admin')} text={m['actions.home']()} />
          </li>
        </ul>
      {/if}
    </div>
    <div class="flex items-center justify-center">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="fr-responsive-img fr-artwork w-[300px]!"
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
