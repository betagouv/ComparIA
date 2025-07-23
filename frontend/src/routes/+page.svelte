<script lang="ts">
  import Footer from '$lib/components/Footer.svelte'
  import FAQContent from '$lib/components/FAQContent.svelte'
  import Newsletter from '$lib/components/Newsletter.svelte'
  import { onMount } from 'svelte'
  import HowItWorks from '$lib/components/HowItWorks.svelte'

  let acceptTos = false
  let showError = false

  onMount(() => {
    // Check for the cookie on component mount
    if (document.cookie.includes('comparia_already_visited')) {
      acceptTos = true
    }
  })

  function handleRedirect() {
    if (acceptTos) {
      window.location.href = '/arene/?cgu_acceptees'
    } else {
      showError = true
    }
  }

  // Reactive statement to hide the error when the user checks the box
  $: if (acceptTos) {
    showError = false
  }
</script>

<main id="content" role="main" class="">
  <section class="fr-grid-row fr-container--fluid bg-blue fr-pb-4w fr-pb-md-10w fr-pt-8w">
    <div class="fr-container-md fr-grid-row">
      <div class="fr-container fr-col-md-5 fr-grid-row">
        <h1>
          Ne vous fiez pas<br />aux réponses<br /><span class="text-purple">d’une seule IA</span>
        </h1>
        <p>Discutez avec deux IA à l’aveugle<br />pour croiser leurs réponses</p>
        <div
          class="fr-checkbox-group fr-checkbox-group--sm fr-mt-3w fr-mb-1w"
          class:fr-checkbox-group--error={showError}
        >
          <input
            aria-describedby="checkbox-error-messages"
            id="accept_tos"
            type="checkbox"
            bind:checked={acceptTos}
          />
          <label class="fr-label fr-text--sm" for="accept_tos">
            J'accepte les&nbsp;<a href="/modalites" target="_blank">modalités d'utilisation</a>
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
        <input
          type="submit"
          id="start_arena_btn"
          class="fr-btn fr-btn--lg bg-light-blue fr-col-md-8 fr-col-12 fr-mb-4w w-full"
          value="Commencer à discuter"
          on:click={handleRedirect}
        />
      </div>
      <div class="fr-col-md-7 bg-blue fr-p-1w fr-p-md-6w">
        <HowItWorks />
      </div>
    </div>
  </section>
  <section class="fr-container--fluid fr-py-4w fr-py-md-8w">
    <h3 class="fr-mb-1w text-center">À quoi sert compar:IA ?</h3>
    <p class="text-grey fr-mb-6w text-center">
      compar:IA est un outil gratuit qui permet de sensibiliser les citoyens à l’IA générative et à
      ses enjeux
    </p>
    <div class="gap fr-container grid">
      <div class="rounded-tile">
        <img
          src="/home/comparer.svg"
          class="fr-responsive-img fr-px-2w fr-py-4w bg-blue"
          alt="Comparer"
        />
        <div class="fr-p-3w">
          <h6 class="fr-mb-1w">Comparer les réponses de différents modèles d’IA</h6>
          <p class="text-grey">
            Discutez et développez votre esprit critique en donnant votre préférence
          </p>
        </div>
      </div>
      <div class="rounded-tile">
        <div class="fr-responsive-img bg-blue">
          <img class="fr-responsive-img" src="/home/mesurer.png" alt="Mesurer" />
        </div>
        <div class="fr-p-3w">
          <h6 class="fr-mb-1w">Tester au même endroit les dernières IA de l’écosystème</h6>
          <p class="text-grey fr-mb-0">
            Testez différents modèles, propriétaires ou non, de petites et grandes tailles
          </p>
        </div>
      </div>
      <div class="rounded-tile">
        <img src="/home/tester.svg" class="fr-responsive-img fr-px-6w fr-py-2w bg-blue bg-blue" />
        <div class="fr-p-3w">
          <h6 class="fr-mb-1w">Mesurer l’empreinte écologique des questions posées aux IA</h6>
          <p class="text-grey">
            Découvrez l’impact environnemental de vos discussions avec chaque modèle
          </p>
        </div>
      </div>
    </div>
  </section>
  <section class="bg-light-grey fr-container--fluid fr-py-4w fr-py-md-6w fr-px-2w fr-px-md-0">
    <div class="fr-container rounded-tile fr-pt-4w fr-pt-md-6w">
      <h4 class="fr-mb-1w text-center">Pourquoi votre vote est-il important ?</h4>
      <p class="text-grey text-center">
        Votre préférence enrichit les jeux de données compar:IA dont l’objectif est d’affiner les
        futurs modèles d’IA sur le français
      </p>
      <div class="fr-grid-row fr-grid-row--gutters">
        <div class="fr-col-12 fr-col-md-4 fr-p-6w text-center">
          <img src="/home/prefs.svg" alt="Vos préférences" width="72" height="72" /><span
            class="arrow-1"
          ></span>
          <h6>Vos préférences</h6>
          <p class="text-grey">
            <br />Après discussion avec les IA, vous indiquez votre préférence pour un modèle selon
            des critères donnés, tels que la pertinence ou l’utilité des réponses
          </p>
        </div>
        <div class="fr-col-12 fr-col-md-4 fr-p-6w text-center">
          <img
            src="/home/datasets.svg"
            alt="Les jeux de données compar:IA"
            width="72"
            height="72"
          /><span class="arrow-2"></span>
          <h6>Les jeux de données<br />compar:IA</h6>
          <p class="text-grey">
            compar:IA compile dans des jeux de données tous les votes et tous les messages partagés
            avec le comparateur
          </p>
        </div>
        <div class="fr-col-12 fr-col-md-4 fr-p-6w text-center">
          <img
            src="/home/finetune.svg"
            alt="Des modèles affinés sur le français"
            width="72"
            height="72"
          />
          <h6 class="fr-mt-1w">Des modèles affinés<br />sur le français</h6>
          <p class="text-grey">
            A terme, les acteurs industriels et académiques peuvent exploiter les jeux de données
            pour entrainer de nouveaux modèles plus respectueux de la diversité linguistique et
            culturelle
          </p>
        </div>
      </div>
      <div class="fr-grid-row fr-grid-row--center fr-my-4w">
        <a
          class="fr-btn purple-btn"
          href="https://huggingface.co/collections/comparIA/jeux-de-donnees-compar-ia-67644adf20912236342c3f3b"
          target="_blank">Accéder aux jeux de données</a
        >
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
  <div class="fr-mt-4w fr-pb-1w text-center">
    <span class="bg-blue fr-py-1w fr-px-3v">
      <a class="fr-link fr-icon-arrow-up-line fr-link--icon-left fr-pb-1v" href="#top">
        Haut de page
      </a>
    </span>
  </div>
  <!-- <section class="bg-light-blue fr-container--fluid"> -->
  <section class="bg-blue fr-container--fluid">
    <div class="grid-2 gap fr-container">
      <div class="fr-pt-4w">
        <h5><span class="fr-icon-mail-line"></span> Abonnez-vous à notre lettre d’information</h5>
        <p>
          Retrouvez les dernières actualités du projet : partenariats, intégration de nouveaux
          modèles, publications de jeux de données et nouvelles fonctionnalités !
        </p>
      </div>
      <div class="fr-mb-4w fr-mb-md-0">
        <Newsletter />
      </div>
    </div>
  </section>
</main>

<Footer></Footer>

<style>
  .fr-checkbox-group input[type='checkbox'] + label:before {
    --border-action-high-blue-france: var(--blue-france-main-525);
  }

  .fr-checkbox-group input[type='checkbox']:checked + label:before {
    --border-active-blue-france: var(--blue-france-main-525);
    background-color: var(--blue-france-main-525);
  }

  .fr-icon-check-line::before,
  .fr-icon-check-line::after {
    -webkit-mask-image: url('assets/dsfr/icons/system/check-line.svg');
    mask-image: url('assets/dsfr/icons/system/check-line.svg');
    background-color: var(--blue-france-main-525);
  }

  .flex {
    display: flex;
  }

  .inline-block {
    display: inline-block;
  }

  .text-purple {
    color: var(--blue-france-main-525);
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

  .bg-light-blue {
    /* --blue-france-main-525: #6A6AF4; */
    --blue-france-main-525-hover: #9898f8;
    --blue-france-main-525-active: #aeaef9;
    --hover: var(--blue-france-main-525-hover);
    --active: var(--blue-france-main-525-active);
    background-color: var(--blue-france-main-525);
  }

  @media (prefers-color-scheme: dark) {
    .bg-blue {
      background-color: #1c1e22;
    }

    .bg-light-grey {
      background-color: #0a0a0b;
    }

    .rounded-tile {
      background-color: black;
    }

    .dark-invert {
      filter: invert(1);
    }
  }

  @media (prefers-color-scheme: light) {
    .bg-light-grey {
      background-color: #fcfcfd;
    }

    .rounded-tile {
      background-color: white;
    }

    #formItem-mbtext-email.fr-input {
      background-color: white;
    }
  }

  .rounded-tile .fr-responsive-img {
    border-top-left-radius: 1rem;
    border-top-right-radius: 1rem;
    min-height: 60%;
  }

  .grid {
    display: grid;
    grid-template-columns: 1fr;
  }

  .grid-2 {
    display: grid;
    grid-template-columns: 1fr;
  }

  @media (min-width: 62em) {
    .grid {
      grid-template-columns: 1fr 1fr 1fr;
    }

    .grid-2 {
      grid-auto-rows: 1fr;
      grid-template-columns: 1fr 1fr;
    }
  }

  .align-center {
    align-items: center;
  }

  .h-full {
    height: 100%;
  }

  .fr-icon-mail-line:after,
  .fr-icon-mail-line:before {
    background-color: var(--blue-france-main-525);
    /* 6A6AF4 */
    -webkit-mask-image: url(assets/dsfr/icons/business/mail-line.svg);
    mask-image: url(assets/dsfr/icons/business/mail-line.svg);
  }

  .fr-icon-arrow-up-line:after,
  .fr-icon-arrow-up-line:before {
    background-color: var(--text-action-high-blue-france);
    -webkit-mask-image: url('assets/dsfr/icons/system/arrow-up-line.svg');
    mask-image: url('assets/dsfr/icons/system/arrow-up-line.svg');
  }

  @media (min-width: 62em) {
    .arrow-1 {
      display: block;
      background-position: right 0px center;
      background-repeat: no-repeat;
      position: relative;
      height: 16px;
      width: 100px;
      left: 100%;
      top: 20px;
      content: '';
      background-image: url('assets/arrow-h.svg');
    }

    .arrow-2 {
      display: block;
      background-position: right 0px center;
      background-repeat: no-repeat;
      position: relative;
      height: 16px;
      width: 100px;
      left: 100%;
      top: 20px;
      content: '';
      background-image: url('assets/arrow-h.svg');
    }
  }
</style>
