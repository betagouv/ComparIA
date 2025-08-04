<script lang="ts">
  import { Button, Link } from '$lib/components/dsfr'
  import FAQContent from '$lib/components/FAQContent.svelte'
  import HowItWorks from '$lib/components/HowItWorks.svelte'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'

  const acceptTos = useLocalStorage('comparia:tos', false)
  let showError = $state(false)

  $effect(() => {
    if (acceptTos.value) showError = false
  })

  function handleRedirect() {
    if (acceptTos.value) {
      window.location.href = '/arene/?cgu_acceptees'
    } else {
      showError = true
    }
  }

  const utilyCards = [
    {
      src: '/home/comparer.svg',
      alt: 'Comparer',
      title: 'Comparer les réponses de différents modèles d’IA',
      desc: 'Discutez et développez votre esprit critique en donnant votre préférence',
      classes: ''
    },
    {
      src: '/home/tester.png',
      alt: 'Tester',
      title: 'Tester au même endroit les dernières IA de l’écosystème',
      desc: 'Testez différents modèles, propriétaires ou non, de petites et grandes tailles',
      classes: ''
    },
    {
      src: '/home/mesurer.svg',
      alt: 'Mesurer',
      title: 'Mesurer l’empreinte écologique des questions posées aux IA',
      desc: 'Découvrez l’impact environnemental de vos discussions avec chaque modèle',
      classes: 'px-14 py-5'
    }
  ]

  const whyVoteCards = [
    {
      src: '/home/prefs.svg',
      title: 'Vos préférences',
      desc: 'Après discussion avec les IA, vous indiquez votre préférence pour un modèle selon des critères donnés, tels que la pertinence ou l’utilité des réponses.'
    },
    {
      src: '/home/datasets.svg',
      title: 'Les jeux de données par langue',
      desc: 'Toutes les questions posées et les votes sont compilées dans des jeux de données et publiés librement après anonmymisation.'
    },
    {
      src: '/home/finetune.svg',
      title: 'Des modèles affinés sur la langue spécifique',
      desc: 'A terme, les acteurs industriels et académiques peuvent exploiter les jeux de données pour entrainer de nouveaux modèles plus respectueux de la diversité linguistique et culturelle.'
    }
  ]
</script>

<main id="content" class="">
  <section class="fr-container--fluid bg-light-grey pb-13 lg:pt-18 pt-10 lg:pb-28">
    <div
      class="fr-container max-w-[1070px]! flex flex-col gap-20 md:flex-row md:items-center md:gap-0"
    >
      <div class="">
        <div class="mb-15 px-4 md:px-0">
          <div class="mb-10 max-w-[280px] md:w-[320px] md:max-w-[320px]">
            <h1 class="mb-5!">
              Ne vous fiez pas aux réponses <span class="text-primary">d’une seule IA</span>
            </h1>

            <p>Discutez avec deux IA à l’aveugle et évaluez leurs réponses</p>
          </div>

          <div
            class="fr-checkbox-group fr-checkbox-group--sm"
            class:fr-checkbox-group--error={showError}
          >
            <input
              aria-describedby="checkbox-error-messages"
              id="accept_tos"
              type="checkbox"
              bind:checked={acceptTos.value}
            />
            <label class="fr-label fr-text--sm block!" for="accept_tos">
              J'accepte les <a href="/modalites" target="_blank"
                >conditions générales d’utilisation</a
              >
              <p class="fr-message">Les données sont partagées à des fins de recherche</p>
            </label>
            <div
              class="fr-messages-group"
              id="checkbox-error-messages"
              aria-live="assertive"
              class:fr-hidden={!showError}
            >
              <p class="fr-message fr-message--error" id="checkbox-error-message-error">
                Vous devez accepter les modalités d'utilisation pour continuer
              </p>
            </div>
          </div>
        </div>

        <Button
          id="start_arena_btn"
          type="submit"
          text="Commencer à discuter"
          size="lg"
          class="w-full! md:max-w-[355px]"
          onclick={handleRedirect}
        />
      </div>
      <div class="bg-light-grey m-auto max-w-[545px] grow px-4 md:me-0 md:px-0">
        <HowItWorks />
      </div>
    </div>
  </section>

  <section class="fr-container--fluid md:py-15 py-10">
    <div class="fr-container">
      <h3 class="mb-3! text-center">À quoi sert compar:IA ?</h3>

      <p class="text-grey mb-8! text-center">
        compar:IA est un outil gratuit qui permet de sensibiliser les citoyens à l’IA générative et
        à ses enjeux
      </p>

      <div class="grid gap-7 md:grid-cols-3">
        {#each utilyCards as card}
          <div class="cg-border">
            <img
              src={card.src}
              alt={card.alt}
              class={[
                'fr-responsive-img h-full! max-h-3/5 sm:max-h-2/3 md:max-h-1/3 lg:max-h-1/2 xl:max-h-3/5 bg-light-grey rounded-t-xl object-contain',
                card.classes
              ]}
            />
            <div class="px-5 pb-7 pt-4 md:px-8 md:pb-10 md:pt-5">
              <h6 class="mb-1! md:mb-2!">{card.title}</h6>
              <p class="text-grey mb-0!">{card.desc}</p>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <section class="fr-container--fluid bg-very-light-grey py-10 lg:py-14">
    <div class="fr-container">
      <div class="cg-border xl:p-13! bg-white px-4 py-10">
        <h4 class="mb-2! text-center">Pourquoi votre vote est-il important ?</h4>

        <p class="text-grey text-center">
          Votre préférence enrichit les jeux de données compar:IA dont l’objectif est d’affiner les
          futurs modèles d’IA sur le français, le suédois, le lituanien et le danois
        </p>

        <div class="md:mt-13 mt-10 flex flex-col text-center lg:flex-row">
          {#each whyVoteCards as card, index}
            <div class="basis-1/3">
              <div class="xl:h-4/7 lg:h-1/2">
                <img src={card.src} alt={card.title} width="72" height="72" class="m-auto mb-4" />
                <h6 class="mb-1! mx-auto! max-w-[230px]">{card.title}</h6>
              </div>
              <p class="m-auto! text-sm! text-grey max-w-[280px]">{card.desc}</p>
            </div>
            {#if index < 2}
              <div class="arrow relative my-5 shrink-0 xl:-me-12 xl:-ms-12"></div>
            {/if}
          {/each}
        </div>

        <div class="lg:mt-19 mt-12 flex justify-center">
          <Link
            button
            hideExternalIcon
            size="lg"
            href="https://huggingface.co/collections/comparIA/jeux-de-donnees-compar-ia-67644adf20912236342c3f3b"
            text="Accéder aux jeux de données"
          />
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container--fluid bg-blue fr-py-8w fr-py-md-10w">
    <div class="fr-container fr-px-md-0">
      <h3 class="fr-mb-1w text-center">Les usages spécifiques de compar:IA</h3>
      <p class="text-grey fr-mb-4w text-center">
        L’outil s’adresse également aux experts IA et aux formateurs pour des usages plus
        spécifiques
      </p>
      <div class="gap grid">
        <div class="rounded-tile fr-p-3w">
          <img src="/icons/database-line.svg" aria-hidden="true" class="fr-mb-2w purple" />
          <h6 class="fr-mb-1w">Exploiter les données</h6>
          <p class="text-grey">
            Développeurs, chercheurs, éditeurs de modèles... accédez aux jeux de données compar:IA
            pour améliorer les modèles
          </p>
        </div>
        <div class="rounded-tile fr-p-3w">
          <img
            src="/icons/search-line.svg"
            aria-hidden="true"
            class="fr-mb-2w"
            width="30"
            height="30"
          />
          <h6 class="fr-mb-1w">Explorer les modèles</h6>
          <p class="text-grey">
            Consultez au même endroit toutes les caractéristiques et conditions d’utilisation des
            modèles
          </p>
        </div>
        <div class="rounded-tile fr-p-3w">
          <img src="/icons/presentation.svg" aria-hidden="true" class="fr-mb-2w" />
          <h6 class="fr-mb-1w">Former et sensibiliser</h6>
          <p class="text-grey">
            Utilisez le comparateur comme un support pédagogique de sensibilisation à l’IA auprès de
            votre public
          </p>
        </div>
      </div>
    </div>
  </section>
  <section class="bg-light-grey fr-container--fluid">
    <div class="fr-px-md-0 grid-2 gap fr-container fr-py-4w fr-py-md-8w">
      <div class="rounded-tile">
        <div class="fr-container fr-py-4w fr-py-md-6w">
          <h5>Qui sommes-nous ?</h5>
          <p>
            Le comparateur compar:IA est développé dans le cadre de la start-up d’Etat compar:IA
            (incubateurs de l’Atelier numérique et AllIAnce) intégrée au programme <a
              href="https://beta.gouv.fr"
              rel="noopener external"
              target="_blank">beta.gouv.fr</a
            > de la Direction interministérielle du numérique (DINUM) qui aide les administrations publiques
            à construire des services numériques utiles, simples et faciles à utiliser.
          </p>
          <div class="fr-grid-row fr-grid-row--center fr-grid-row--middle fr-grid-row--gutters">
            <div class="fr-col-md-4 fr-col-6">
              <img
                class=""
                src="/orgs/minicult.svg"
                alt="Ministère de la Culture"
                title="Ministère de la Culture"
                width="137px"
                height="97px"
              />
            </div>
            <div class="fr-col-md-4 fr-col-6 text-center">
              <img
                class="dark-invert lol"
                src="/orgs/ateliernumerique.png"
                alt="Atelier numérique"
                title="Atelier numérique"
                width="105px"
                height="105px"
              />
            </div>
            <div class="fr-col-md-4 fr-col-12">
              <img
                src="/orgs/betagouv.svg"
                alt="beta.gouv.fr"
                title="beta.gouv.fr"
                class="dark-invert fr-responsive-img"
                width="191px"
                height="65px"
              />
              <img
                src="/orgs/dinum.png"
                class="dark-invert fr-responsive-img"
                alt="DINUM"
                title="DINUM"
                width="278px"
                height="59px"
              />
            </div>
          </div>
        </div>
      </div>
      <div class="fr-container rounded-tile">
        <div class="fr-container fr-py-4w fr-py-md-6w fr-px-md-2w">
          <h5>Quelles sont nos missions ?</h5>
          <div class="fr-grid-row fr-grid-row--top">
            <img
              src="/icons/map-pin.svg"
              alt="Point sur la carte"
              aria-hidden="true"
              class="fr-col-1 fr-pr-md-1w"
            />
            <div class="fr-col-11 fr-pl-1w">
              <h6 class="fr-mb-0 fr-text--lg">Faciliter l’accès</h6>
              <p class="text-grey">
                Mise à disposition de plusieurs modèles d’IA conversationnels à travers une unique
                plateforme.
              </p>
            </div>
            <img
              src="/icons/database-line.svg"
              alt="jeux de données"
              class="fr-col-1 fr-pr-md-1w"
            />
            <div class="fr-col-11 fr-pl-1w">
              <h6 class="fr-mb-0 fr-text--lg">Collecter des données</h6>
              <p class="text-grey">
                Création de jeux de données de préférence à partir de tâches réelles, utiles pour
                l’alignement des modèles en français.
              </p>
            </div>
            <img
              src="/icons/share.svg"
              alt="écosystème"
              aria-hidden="true"
              class="fr-col-1 fr-pr-md-1w"
            />
            <div class="fr-col-11 fr-pl-1w">
              <h6 class="fr-mb-0 fr-text--lg">Partager</h6>
              <p class="text-grey">
                Diffusion sous licence ouverte des jeux de données générées pour en faire bénéficier
                l’écosystème IA.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
  <section>
    <div class="fr-container">
      <h3 class="fr-mt-md-8w fr-mt-4w fr-pb-2w text-center">Vos questions les plus courantes</h3>
      <FAQContent />
      <div class="fr-mt-4w fr-mb-8w text-center">
        <a class="fr-btn purple-btn" href="/faq">Découvrir les autres questions</a>
      </div>
    </div>
  </section>
</main>

<style lang="postcss">
  .fr-checkbox-group input[type='checkbox'] + label:before {
    --border-action-high-blue-france: var(--blue-france-main-525);
  }

  .fr-checkbox-group input[type='checkbox']:checked + label:before {
    --border-active-blue-france: var(--blue-france-main-525);
    background-color: var(--blue-france-main-525);
  }

  .rounded-tile {
    border-color: #e5e5e5;
    border-width: 1px;
    border-style: solid;
    border-radius: 1rem;
  }

  .bg-blue {
    /* background-color: var(--blue-france-975-75); */
    /* --background-contrast-info: var(--info-950-100); */
    /* background-color: var(--background-contrast-info); */
    background-color: #f3f5f9;
  }

  @media (prefers-color-scheme: dark) {
    .rounded-tile {
      background-color: black;
    }

    .dark-invert {
      filter: invert(1);
    }
  }

  @media (prefers-color-scheme: light) {
    .rounded-tile {
      background-color: white;
    }
  }

  .rounded-tile .fr-responsive-img {
    border-top-left-radius: 1rem;
    border-top-right-radius: 1rem;
    min-height: 60%;
  }

  .arrow {
    height: 62px;
    width: 16px;
    background-image: url('/home/arrow-h-mobile.svg');
    left: calc(50% - 8px);

    @media (min-width: 62em) {
      & {
        height: 16px;
        width: 125px;
        background-image: url('/home/arrow-h.svg');
        left: 0;
        margin-top: 110px;
      }
    }
  }
</style>
