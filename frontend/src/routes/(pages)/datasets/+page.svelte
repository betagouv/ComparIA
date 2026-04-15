<script lang="ts">
  import { Link } from '$components/dsfr'
  import SeoHead from '$components/SEOHead.svelte'
  import { getI18nContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'

  const locale = getLocale()
  const i18nData = getI18nContext()

  const datasetCards = (
    [
      {
        i18nKey: 'conversations',
        img: `/datasets/conversations-${locale === 'fr' ? 'fr' : 'en'}.png`,
        link: 'https://huggingface.co/datasets/ArthurSrz/comparag-tool-votes'
      },
      {
        i18nKey: 'reactions',
        img: `/datasets/reactions-${locale === 'fr' ? 'fr' : 'en'}.png`,
        link: 'https://huggingface.co/datasets/ArthurSrz/comparag-tool-votes'
      },
      {
        i18nKey: 'votes',
        img: `/datasets/votes-${locale === 'fr' ? 'fr' : 'en'}.png`,
        link: 'https://huggingface.co/datasets/ArthurSrz/comparag-tool-votes'
      }
    ] as const
  ).map(({ i18nKey, ...card }) => ({
    ...card,
    title: m[`datasets.access.repos.${i18nKey}.title`](),
    desc: m[`datasets.access.repos.${i18nKey}.desc`]()
  }))

  const bunkaCards = (
    [
      {
        i18nKey: 'conversations',
        img: '/datasets/bunka-visualisation.png',
        link: 'https://app.bunka.ai/datasets/569'
      },
      {
        i18nKey: 'analyze',
        img: '/datasets/bunka-analyse.png',
        link: 'https://monitor.bunka.ai/compar-ia-dashboard'
      }
    ] as const
  ).map(({ i18nKey, ...card }) => ({
    ...card,
    linkTitle: m[`datasets.reuse.bunka.${i18nKey}.title`](),
    desc: m[`datasets.reuse.bunka.${i18nKey}.desc`]()
  }))
</script>

<SeoHead title={m['seo.titles.datasets']()} />

<main>
  <section class="fr-container--fluid bg-light-info py-6!">
    <div class="fr-container">
      <div class="cg-border gap-8 bg-white px-5 py-8 md:px-8 md:py-10 lg:grid-cols-2 grid">
        <div>
          <h2 class="fr-h6">{m['datasets.access.title']()}</h2>
          <p>
            {@html sanitize(
              m['datasets.access.desc']({
                linkProps: externalLinkProps({
                  href: 'https://huggingface.co/datasets/ArthurSrz/comparag-tool-votes',
                  class: 'text-primary!'
                })
              })
            )}
          </p>
          <p><strong>{m['datasets.access.catch']()}</strong></p>
          <Link
            button
            variant="secondary"
            href="mailto:{i18nData.contact}"
            text={m['datasets.access.share']()}
            class="md:w-auto! w-full!"
          />
        </div>

        <div
          class="gap-4 sm:grid-cols-3 md:content-center md:gap-6 lg:grid-cols-2 xl:grid-cols-3 grid grid-cols-2"
        >
          {#each datasetCards as card, i (i)}
            <div class="cg-border bg-very-light-grey">
              <img
                src={card.img}
                class="fr-responsive-img rounded-t-xl"
                data-fr-js-ratio="true"
                aria-hidden="true"
                alt=""
              />
              <div class="px-3 pt-2 pb-4">
                <p class="mb-1! text-sm!">
                  <Link variant="primary" href={card.link} text={card.title} native={false} />
                </p>
                <p class="mb-0! text-xs! text-grey">{card.desc}</p>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container mb-20 py-8!">
    <div class="fr-container cg-border rounded-2xl bg-light-grey p-8! md:p-14! text-center">
      <p class="fr-h4 mb-4!">🤝 Vous avez réutilisé ce jeu de données ?</p>
      <p class="mb-8! text-grey max-w-2xl mx-auto">
        Ce jeu de données est libre d'accès et conçu pour être réutilisé. Que vous soyez chercheur, développeur ou entreprise, nous vous invitons à explorer ces données et à partager vos analyses, visualisations ou modèles avec la communauté.
      </p>
      <Link
        button
        href="mailto:{i18nData.contact}"
        text="Partagez votre réutilisation"
        class="sm:w-auto! w-full!"
      />
    </div>
  </section>
</main>

<style lang="postcss">
  main {
    p {
      font-size: 0.875rem;

      @media (min-width: 48em) {
        & {
          font-size: 1rem;
        }
      }
    }

    p,
    h2 {
      line-height: 1.5em;
    }
  }
</style>
