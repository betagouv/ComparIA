<script>
  import SeoHead from '$lib/components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
</script>

<SeoHead title={m['seo.titles.datasets']()} />

<main id="content" role="main" class="">
  <section class="fr-container--fluid bg-blue fr-py-5v">
    <div class="fr-container">
      <div
        class="fr-container--fluid rounded-tile grid-2-lg fr-px-5v fr-py-4w fr-px-md-4w fr-py-md-5w bg-white"
      >
        <div>
          <h2 class="title-small">Accédez aux jeux de données compar:IA</h2>
          <p>
            Les questions et préférences posées sur la plateforme sont majoritairement en français
            et reflètent des usages réels et non contraints. Ces jeux de données sont accessibles
            sur <a href="https://www.data.gouv.fr" rel="noopener external" target="_blank"
              >data.gouv</a
            > et Hugging Face.
          </p>
          <p>
            <strong
              >Editeurs de modèles, chercheurs, chercheuses, entreprises, à vous de jouer !</strong
            >
          </p>
          <a
            href="mailto:contact@comparia.beta.gouv.fr"
            class="fr-btn fr-btn--secondary"
            rel="noopener external"
            target="_blank">Partagez-nous vos réutilisations</a
          >
        </div>

        <div class="grid-3">
          <div class="rounded-tile bg-light-grey">
            <img
              src="/datasets/conversations.png"
              class="fr-responsive-img"
              data-fr-js-ratio="true"
            />
            <div class="fr-px-3v fr-pt-1w fr-pb-2w">
              <p class="text-small fr-mb-1v">
                <a
                  href="https://huggingface.co/datasets/ministere-culture/comparia-conversations"
                  rel="noopener external"
                  target="_blank">/conversations</a
                >
              </p>
              <p class="text-tiny text-grey fr-mb-0">
                Ensemble des réponses et des questions posées
              </p>
            </div>
          </div>
          <div class="rounded-tile bg-light-grey">
            <img
              src="/datasets/reactions.png"
              class="fr-responsive-img"
              data-fr-js-ratio="true"
            />
            <div class="fr-px-3v fr-pt-1w fr-pb-2w">
              <p class="text-small fr-mb-1v">
                <a
                  href="https://huggingface.co/datasets/ministere-culture/comparia-reactions"
                  rel="noopener external"
                  target="_blank">/réactions</a
                >
              </p>
              <p class="text-tiny text-grey fr-mb-0">Ensemble des réactions exprimées</p>
            </div>
          </div>
          <div class="rounded-tile bg-light-grey">
            <img
              src="/datasets/votes.png"
              class="fr-responsive-img"
              data-fr-js-ratio="true"
            />
            <div class="fr-px-3v fr-pt-1w fr-pb-2w">
              <p class="text-small fr-mb-1v">
                <a
                  href="https://huggingface.co/datasets/ministere-culture/comparia-votes"
                  rel="noopener external"
                  target="_blank">/votes</a
                >
              </p>
              <p class="text-tiny text-grey fr-mb-0">Ensemble des préférences exprimées</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container fr-py-4w fr-mb-10w">
    <h2 class="title-large fr-mb-2w text-center">Comment ces données sont-elles utilisées ?</h2>
    <p class="text-grey fr-mb-5w fr-px-5w text-center">
      Exemples de réutilisation des jeux de données compar:IA
    </p>

    <div class="fr-container rounded-tile-large bg-dark-grey fr-p-5v fr-p-md-5w">
      <div class="bunka fr-pb-4w">
        <img src="/datasets/bunka-ai-logo.jpg" class="fr-mr-md-4w" />
        <p class="fr-mb-0">
          L'équipe Bunka.ai a mené une étude approfondie sur les interactions entre les utilisateurs
          de la plateforme Compar:IA et les modèles d'IA, examinant les thématiques privilégiées,
          les tâches principales et déterminant si ces modèles fonctionnent avant tout comme des
          outils d'automatisation ou d'augmentation des capacités humaines. Cette analyse repose sur
          un large échantillon de 25 000 conversations.
        </p>
      </div>

      <div class="">
        <div class="grid-2-md">
          <div
            class="fr-container bg-light-grey rounded-tile no-border flex-column fr-px-3v fr-py-5v fr-px-md-5w fr-py-md-4w"
          >
            <div class="fr-px-2v fr-p-md-0">
              <img src="/datasets/bunka-visualisation.png" class="fr-responsive-img" />
              <p class="text-grey text-small fr-py-5v fr-m-0">
                Visualisation interactive des conversations où chaque point représente un cluster de
                discussions évoqué par les utilisateurs (comme l’éducation, la santé,
                l’environnement, ou encore la philosophie).
              </p>
            </div>
            <a
              href="https://app.bunka.ai/datasets/569"
              class="fr-btn purple-btn btn-full fr-mt-auto"
              rel="noopener external"
              target="_blank">Explorer la visualisation de données</a
            >
          </div>

          <div
            class="fr-container bg-light-grey rounded-tile no-border flex-column fr-px-3v fr-py-5v fr-px-md-5w fr-py-md-4w"
          >
            <div class="fr-px-2v fr-p-md-0">
              <img src="/datasets/bunka-analyse.png" class="fr-responsive-img" />
              <p class="text-grey text-small fr-py-5v fr-m-0">
                Analyse des conversations des utilisateurs avec détection des tâches (création,
                recherche d'informations...), des sujets (arts et culture, éducation...), des
                émotions complexes (curiosité, enthousiasme...), des types de langage (formel,
                professionnel...)
              </p>
            </div>
            <a
              href="https://monitor.bunka.ai/compar-ia-dashboard"
              class="fr-btn purple-btn btn-full fr-mt-auto"
              rel="noopener external"
              target="_blank">Accéder à l’analyse par indicateur</a
            >
          </div>
        </div>

        <div class="fr-mt-9v text-center">
          <a
            href="https://bunka.ai/fr/articles/french-ai-usage-study"
            rel="noopener external"
            target="_blank"
            class="text-center">En savoir plus sur la méthodologie</a
          >
        </div>
      </div>
    </div>
  </section>
</main>

<style>
  .bg-white {
    background-color: #fff;
  }

  .bg-dark-grey {
    background-color: #f3f5f9;
  }

  .bg-blue {
    background-color: var(--info-950-100);
  }

  .bg-light-grey {
    background-color: #f9fafb;
  }

  @media (prefers-color-scheme: dark) {
    .bg-white {
      background-color: #000;
    }

    .bg-blue {
      background-color: #1c1e22;
    }

    .bg-dark-grey {
      background-color: #0a0a0b;
    }

    .bg-light-grey {
      background-color: #1c1e22;
    }
  }

  main a {
    color: var(--blue-france-main-525);
  }

  .rounded-tile,
  .rounded-tile-large,
  .rounded-tile-border {
    border-radius: 12px;
    border: 1px solid #e5e5e5;
  }

  .rounded-tile-large {
    border-radius: 20px;
  }

  .rounded-tile > .fr-responsive-img {
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
  }

  .no-border {
    border: unset;
  }

  .w-full {
    width: 100%;
  }

  .flex-column {
    display: flex;
    flex-direction: column;
  }

  .text-center {
    text-align: center;
  }

  .btn-full {
    width: 100%;
    justify-content: center;
  }

  .fr-btn--secondary {
    box-shadow: inset 0 0 0 1px var(--blue-france-main-525);
    color: var(--blue-france-main-525);
  }

  .bunka img {
    width: 100px;
    height: 100px;
    border-radius: 15px;
  }

  .grid-2-md {
    display: grid;
    gap: 20px;
  }

  .grid-2-lg {
    display: grid;
    gap: 30px;
  }

  .grid-3 {
    display: grid;
    gap: 10px;
    grid-template-columns: 1fr 1fr;
    grid-auto-rows: 1fr;
  }

  @media screen and (max-width: 767px) {
    main p {
      font-size: 14px;
    }

    .title-large {
      font-size: 22px;
      margin-bottom: 20px;
    }

    .title-small {
      font-size: 18px;
      margin-bottom: 8px;
    }

    .text-small {
      font-size: 12px;
    }

    .text-tiny {
      font-size: 10px;
    }

    .bunka img {
      margin-bottom: 8px;
    }

    .purple-btn {
      font-size: 14px;
      line-height: 1.5em;
      padding: 4px 8px 4px 12px;
    }

    .btn-outline {
      width: 100%;
      justify-content: center;
    }
  }

  @media screen and (min-width: 768px) {
    .title-large {
      font-size: 24px;
      margin-bottom: 10px;
    }

    .title-small {
      font-size: 20px;
    }

    .text-small {
      font-size: 14px;
    }

    .text-tiny {
      font-size: 12px;
    }

    .bunka {
      display: flex;
    }

    .grid-2-md {
      grid-template-columns: 1fr 1fr;
      grid-auto-rows: 1fr;
      gap: 40px;
    }

    .grid-2-lg {
      grid-auto-rows: 1fr;
    }

    .grid-3 {
      gap: 25px;
      grid-template-columns: 1fr 1fr 1fr;
    }
  }

  @media (min-width: 62em) {
    .grid-2-lg {
      grid-template-columns: 1fr 1fr;
      grid-auto-rows: 1fr;
      gap: 40px;
      justify-content: center;
    }

    .grid-3 {
      grid-auto-rows: max-content;
      align-content: center;
    }
  }

  main p,
  main h2 {
    line-height: 1.5em;
  }
</style>
