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
        link: 'https://huggingface.co/datasets/ministere-culture/comparia-conversations'
      },
      {
        i18nKey: 'reactions',
        img: `/datasets/reactions-${locale === 'fr' ? 'fr' : 'en'}.png`,
        link: 'https://huggingface.co/datasets/ministere-culture/comparia-reactions'
      },
      {
        i18nKey: 'votes',
        img: `/datasets/votes-${locale === 'fr' ? 'fr' : 'en'}.png`,
        link: 'https://huggingface.co/datasets/ministere-culture/comparia-votes'
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
      <div class="cg-border grid gap-8 bg-white px-5 py-8 md:px-8 md:py-10 lg:grid-cols-2">
        <div>
          <h2 class="fr-h6">{m['datasets.access.title']()}</h2>
          <p>
            {@html sanitize(
              m['datasets.access.desc']({
                linkProps: externalLinkProps({
                  href: 'https://www.data.gouv.fr/datasets/compar-ia/',
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
            class="w-full! md:w-auto!"
          />
        </div>

        <div
          class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:content-center md:gap-6 lg:grid-cols-2 xl:grid-cols-3"
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
    <h2 class="fr-h4 mb-4! text-center">{m['datasets.reuse.title']()}</h2>
    <p class="mb-10! px-10! text-center text-grey">{m['datasets.reuse.desc']()}</p>

    <div class="fr-container cg-border rounded-2xl bg-light-grey p-5! md:p-10!">
      <div class="pb-8 md:flex">
        <img
          src="/datasets/bunka-ai-logo.jpg"
          class="mb-2 block h-[100px] w-[100px] rounded-2xl md:mr-8 md:mb-0"
          alt="Bunka.ai"
        />
        <p class="mb-0!">{m['datasets.reuse.bunka.desc']()}</p>
      </div>

      <div>
        <div class="grid gap-5 md:grid-cols-2 md:grid-rows-1 md:gap-10">
          {#each bunkaCards as card, i (i)}
            <div
              class="fr-container flex flex-col rounded-xl bg-very-light-grey px-3! py-5! md:px-10! md:py-8!"
            >
              <div class="px-2 md:p-0">
                <img src={card.img} class="fr-responsive-img" alt="" aria-hidden="true" />
                <p class="m-0! py-5! text-sm! text-grey">{card.desc}</p>
              </div>
              <Link
                button
                href={card.link}
                text={card.linkTitle}
                class="mt-auto w-full! text-center!"
              />
            </div>
          {/each}
        </div>

        <div class="mt-9 text-center">
          <Link
            href="https://bunka.ai/fr/articles/french-ai-usage-study"
            text={m['datasets.reuse.bunka.method']()}
            class="text-center"
            native={false}
          />
        </div>
      </div>
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
