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

  const europeCards = [
    {
      title: '/compar:IA',
      link: 'https://comparia.beta.gouv.fr/',
      desc: 'en français',
      flag: '🇫🇷'
    },
    {
      title: '/palyginti:AI',
      link: 'https://comparia.beta.gouv.fr/',
      desc: 'en lituanien',
      flag: '🇱🇹'
    },
    {
      title: '/jämföra:AI',
      link: 'https://comparia.beta.gouv.fr/',
      desc: 'en suédois',
      flag: '🇸🇪'
    },
    {
      title: '/xxxxxx:AI',
      link: 'https://comparia.beta.gouv.fr/',
      desc: 'en danois',
      flag: '🇩🇰'
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

  const usageCards = [
    {
      src: '/icons/database-line.svg',
      title: 'Exploiter les données',
      desc: 'Développeurs, chercheurs, éditeurs de modèles... accédez aux jeux de données compar:IA pour améliorer les modèles'
    },
    {
      src: '/icons/search-line.svg',
      title: 'Explorer les modèles',
      desc: 'Consultez au même endroit toutes les caractéristiques et conditions d’utilisation des modèles'
    },
    {
      src: '/icons/presentation.svg',
      title: 'Former et sensibiliser',
      desc: 'Utilisez le comparateur comme un support pédagogique de sensibilisation à l’IA auprès de votre public'
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

  <section id="european" class="fr-container--fluid bg-light-info pb-18 lg:pb-25 pt-10 lg:pt-20">
    <div class="fr-container max-w-[1150px]! flex flex-col gap-8 lg:flex-row lg:items-center">
      <div class="max-w-[360px]">
        <h3 class="mb-4! fr-h2 max-w-[320px]">
          Le comparateur <span class="text-primary">devient européen !</span>
        </h3>

        <p class="mb-2!">
          La Lituanie, la Suède et le Danemark rejoignent la France en adoptant le comparateur dans
          le but d’affiner les futurs modèles d’IA dans leurs langues nationales.
        </p>
        <p>
          <strong class="block">
            Vous souhaitez également disposer du comparateur dans votre langue ?
          </strong>
        </p>

        <Link button size="lg" href="FIXME" text="Nous contacter" />
      </div>

      <div
        class="py-15 flex w-full flex-col justify-center gap-8 rounded-xl bg-white px-9 xl:flex-row"
      >
        <img src="/home/comparia-stars.svg" alt="FIXME" class="m-auto max-w-fit xl:m-0" />

        <div class="grid gap-4 sm:grid-cols-2 xl:gap-8">
          {#each europeCards as card}
            <div class="cg-border bg-very-light-grey flex items-center gap-4 px-4 py-5">
              <div class="bg-light-info p-2 leading-none">
                {card.flag}
              </div>
              <div>
                <Link
                  href={card.link}
                  variant="primary"
                  native={false}
                  text={card.title}
                  size="sm"
                />
                <p class="mb-0! fr-message">{card.desc}</p>
              </div>
            </div>
          {/each}
        </div>
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

  <section class="fr-container--fluid bg-light-grey py-10 lg:py-20">
    <div class="fr-container">
      <h3 class="mb-2! text-center">Les usages spécifiques de compar:IA</h3>

      <p class="text-grey fr-mb-4w text-center">
        L’outil s’adresse également aux experts IA et aux formateurs pour des usages plus
        spécifiques
      </p>

      <div class="grid gap-8 md:grid-cols-3">
        {#each usageCards as card}
          <div class="cg-border bg-white p-5 lg:px-8 lg:pb-11 lg:pt-6">
            <img src={card.src} alt="" aria-hidden="true" width="30" height="30" class="mb-4" />
            <h6 class="mb-2!">{card.title}</h6>
            <p class="text-grey mb-0!">{card.desc}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <section class="fr-container--fluid bg-very-light-grey lg:pb-38 py-12 lg:pt-20">
    <div class="fr-container grid gap-10 lg:grid-cols-2 lg:gap-6">
      <div class="cg-border bg-white px-5 py-10 md:px-8">
        <h5>Qui sommes-nous ?</h5>

        <p>
          Le comparateur est porté au sein du Ministère de la Culture par une équipe
          pluridisciplinaire réunissant expert en Intelligence artificielle, développeurs, chargé de
          déploiement, designer, avec pour mission de rendre les IA conversationnelles plus
          transparentes et accessibles à toutes et tous.
        </p>

        <div class="mt-12 flex gap-8">
          <img
            class="max-h-[95px]"
            src="/orgs/minicult.svg"
            alt="Ministère de la Culture"
            title="Ministère de la Culture"
          />
          <img
            class="max-h-[95px] dark:invert"
            src="/orgs/ateliernumerique.png"
            alt="Atelier numérique"
            title="Atelier numérique"
          />
        </div>
      </div>

      <div class="cg-border bg-white px-5 py-10 md:px-8">
        <h5>Qui est à l’origine du projet ?</h5>

        <p>
          Le comparateur a été conçu et développé dans le cadre d’une start-up d’Etat portée par le
          ministère de la Culture et intégrée au programme <a
            href="https://beta.gouv.fr"
            rel="noopener external"
            target="_blank">Beta.gouv.fr</a
          > de la Direction interministérielle du numérique (DINUM) qui aide les administrations publiques
          françaises à construire des services numériques utiles, simples et faciles à utiliser.
        </p>

        <div class="mt-12 flex gap-8">
          <img
            src="/orgs/betagouv.svg"
            alt="beta.gouv.fr"
            title="beta.gouv.fr"
            class="max-w-[178px] dark:invert"
            width="191px"
            height="65px"
          />
          <img
            src="/orgs/dinum.png"
            class="max-w-[254px] dark:invert"
            alt="DINUM"
            title="DINUM"
            width="278px"
            height="59px"
          />
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container--fluid pb-18 lg:pb-25 pt-10 lg:pt-20">
    <div class="fr-container">
      <h3 class="mb-8! lg:mb-10! text-center">Vos questions les plus courantes</h3>

      <FAQContent />

      <div class="mt-8 text-center lg:mt-11">
        <Link button size="lg" href="/faq" text="Découvrir les autres questions" />
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
