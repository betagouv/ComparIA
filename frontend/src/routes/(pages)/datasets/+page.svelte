<script lang="ts">
  import Link from '$lib/components/dsfr/Link.svelte'
  import SeoHead from '$lib/components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'

  const datasetCards = (
    [
      {
        i18nKey: 'conversations',
        img: '/datasets/conversations.png',
        link: 'https://huggingface.co/datasets/ministere-culture/comparia-conversations',
        title: '/conversations',
        desc: 'Ensemble des réponses et des questions posées'
      },
      {
        i18nKey: 'reactions',
        img: '/datasets/reactions.png',
        link: 'https://huggingface.co/datasets/ministere-culture/comparia-reactions',
        title: '/réactions',
        desc: 'Ensemble des réactions exprimées'
      },
      {
        i18nKey: 'votes',
        img: '/datasets/votes.png',
        link: 'https://huggingface.co/datasets/ministere-culture/comparia-votes',
        title: '/votes',
        desc: 'Ensemble des préférences exprimées'
      }
    ] as const
  ).map(({ i18nKey, ...card }) => ({
    ...card
    // title: m[`datasets.types.${i18nKey}.title`](),
    // desc: m[`datasets.types.${i18nKey}.desc`]()
  }))

  const bunkaCards = (
    [
      {
        i18nKey: 'conversations',
        img: '/datasets/bunka-visualisation.png',
        desc: 'Visualisation interactive des conversations où chaque point représente un cluster de discussions évoqué par les utilisateurs (comme l’éducation, la santé, l’environnement, ou encore la philosophie).',
        link: 'https://app.bunka.ai/datasets/569',
        linkTitle: 'Explorer la visualisation de données'
      },
      {
        i18nKey: 'analyse',
        img: '/datasets/bunka-analyse.png',
        desc: "Analyse des conversations des utilisateurs avec détection des tâches (création, recherche d'informations...), des sujets (arts et culture, éducation...), des émotions complexes (curiosité, enthousiasme...), des types de langage (formel, professionnel...)",
        link: 'https://monitor.bunka.ai/compar-ia-dashboard',
        linkTitle: 'Accéder à l’analyse par indicateur'
      }
    ] as const
  ).map(({ i18nKey, ...card }) => ({
    ...card
    // linkTitle: m[`datasets.bunka.dataviz.${i18nKey}.title`](),
    // desc: m[`datasets.bunka.dataviz.${i18nKey}.desc`]()
  }))
</script>

<SeoHead title={m['seo.titles.datasets']()} />

<main>
  <section class="fr-container--fluid bg-light-info py-6!">
    <div class="fr-container">
      <div class="cg-border grid gap-8 bg-white px-5 py-8 md:px-8 md:py-10 lg:grid-cols-2">
        <div>
          <h2 class="fr-h6">Accédez aux jeux de données compar:IA</h2>
          <p>
            Les questions et préférences posées sur la plateforme sont majoritairement en français
            et reflètent des usages réels et non contraints. Ces jeux de données sont accessibles
            sur <a
              href="https://www.data.gouv.fr"
              rel="noopener external"
              target="_blank"
              class="text-primary!">data.gouv</a
            > et Hugging Face.
          </p>
          <p>
            <strong
              >Editeurs de modèles, chercheurs, chercheuses, entreprises, à vous de jouer !</strong
            >
          </p>
          <Link
            button
            variant="secondary"
            href="mailto:contact@comparia.beta.gouv.fr"
            text={'Partagez-nous vos réutilisations'}
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
    <h2 class="fr-h4 mb-4! text-center">Comment ces données sont-elles utilisées ?</h2>
    <p class="text-grey mb-10! px-10! text-center">
      Exemples de réutilisation des jeux de données compar:IA
    </p>

    <div class="fr-container cg-border bg-light-grey p-5! md:p-10! rounded-2xl">
      <div class="pb-8 md:flex">
        <img
          src="/datasets/bunka-ai-logo.jpg"
          class="mb-2 block h-[100px] w-[100px] rounded-2xl md:mb-0 md:mr-8"
        />
        <p class="mb-0!">
          L'équipe Bunka.ai a mené une étude approfondie sur les interactions entre les utilisateurs
          de la plateforme Compar:IA et les modèles d'IA, examinant les thématiques privilégiées,
          les tâches principales et déterminant si ces modèles fonctionnent avant tout comme des
          outils d'automatisation ou d'augmentation des capacités humaines. Cette analyse repose sur
          un large échantillon de 25 000 conversations.
        </p>
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
              <Link button href={card.link} text={card.linkTitle} class="w-full! mt-auto" />
            </div>
          {/each}
        </div>

        <div class="mt-9 text-center">
          <Link
            href="https://bunka.ai/fr/articles/french-ai-usage-study"
            text={'En savoir plus sur la méthodologie'}
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
