<script lang="ts">
  import { Link } from '$components/dsfr'
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'

  const datasetCards = (
    [
      {
        i18nKey: 'conversations',
        img: '/datasets/conversations.png',
        link: 'https://huggingface.co/datasets/ministere-culture/comparia-conversations'
      },
      {
        i18nKey: 'reactions',
        img: '/datasets/reactions.png',
        link: 'https://huggingface.co/datasets/ministere-culture/comparia-reactions'
      },
      {
        i18nKey: 'votes',
        img: '/datasets/votes.png',
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
            href="mailto:contact@comparia.beta.gouv.fr"
            text={m['datasets.access.share']()}
            class="w-full! md:w-auto!"
          />
        </div>

        <div
          class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:content-center md:gap-6 lg:grid-cols-2 xl:grid-cols-3"
        >
          {#each datasetCards as card}
            <div class="cg-border bg-very-light-grey">
              <img
                src={card.img}
                class="fr-responsive-img rounded-t-xl"
                data-fr-js-ratio="true"
                aria-hidden="true"
                alt=""
              />
              <div class="px-3 pb-4 pt-2">
                <p class="text-sm! mb-1!">
                  <Link variant="primary" href={card.link} text={card.title} native={false} />
                </p>
                <p class="text-xs! text-grey mb-0!">{card.desc}</p>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container py-8! mb-20">
    <h2 class="fr-h4 mb-4! text-center">{m['datasets.reuse.title']()}</h2>
    <p class="text-grey mb-10! px-10! text-center">{m['datasets.reuse.desc']()}</p>

    <div class="fr-container cg-border bg-light-grey p-5! md:p-10! rounded-2xl">
      <div class="pb-8 md:flex">
        <img
          src="/datasets/bunka-ai-logo.jpg"
          class="mb-2 block h-[100px] w-[100px] rounded-2xl md:mb-0 md:mr-8"
        />
        <p class="mb-0!">{m['datasets.reuse.bunka.desc']()}</p>
      </div>

      <div>
        <div class="grid gap-5 md:grid-cols-2 md:grid-rows-1 md:gap-10">
          {#each bunkaCards as card}
            <div
              class="fr-container bg-very-light-grey px-3! py-5! md:px-10! md:py-8! flex flex-col rounded-xl"
            >
              <div class="px-2 md:p-0">
                <img src={card.img} class="fr-responsive-img" />
                <p class="text-grey text-sm! py-5! m-0!">{card.desc}</p>
              </div>
              <Link
                button
                href={card.link}
                text={card.linkTitle}
                class="w-full! text-center! mt-auto"
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
