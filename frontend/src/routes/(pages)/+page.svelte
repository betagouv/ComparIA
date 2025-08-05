<script lang="ts">
  import { Button, Link } from '$lib/components/dsfr'
  import FAQContent from '$lib/components/FAQContent.svelte'
  import HowItWorks from '$lib/components/HowItWorks.svelte'
  import Newsletter from '$lib/components/Newsletter.svelte'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale, type Locale } from '$lib/i18n/runtime'
  import { externalLinkProps, propsToAttrs, sanitize } from '$lib/utils/commons'
  import type { HTMLImgAttributes } from 'svelte/elements'

  const locale = getLocale()
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

  const utilyCards = (
    [
      { i18nKey: 'compare', src: '/home/comparer.svg', classes: '' },
      { i18nKey: 'test', src: '/home/tester.png', classes: '' },
      { i18nKey: 'measure', src: '/home/mesurer.svg', classes: 'px-14 py-5' }
    ] as const
  ).map(({ i18nKey, ...card }) => ({
    ...card,
    title: m[`home.use.${i18nKey}.title`](),
    desc: m[`home.use.${i18nKey}.desc`](),
    alt: m[`home.use.${i18nKey}.alt`]()
  }))

  const europeCards = [
    {
      title: '/compar:IA',
      link: 'https://comparia.beta.gouv.fr/',
      desc: m['home.europe.languages.fr'](),
      flag: '🇫🇷'
    },
    {
      title: '/palyginti:AI',
      link: 'https://comparia.beta.gouv.fr/',
      desc: m['home.europe.languages.lt'](),
      flag: '🇱🇹'
    },
    {
      title: '/jämföra:AI',
      link: 'https://comparia.beta.gouv.fr/',
      desc: m['home.europe.languages.se'](),
      flag: '🇸🇪'
    },
    {
      title: '/xxxxxx:AI',
      link: 'https://comparia.beta.gouv.fr/',
      desc: m['home.europe.languages.da'](),
      flag: '🇩🇰'
    }
  ]

  const whyVoteCards = (
    [
      { i18nKey: 'prefs', src: '/home/prefs.svg' },
      { i18nKey: 'datasets', src: '/home/datasets.svg' },
      { i18nKey: 'finetune', src: '/home/finetune.svg' }
    ] as const
  ).map(({ i18nKey, ...card }) => ({
    ...card,
    title: m[`home.vote.steps.${i18nKey}.title`](),
    desc: m[`home.vote.steps.${i18nKey}.desc`]()
  }))

  const usageCards = (
    [
      { i18nKey: 'use', src: '/icons/database-line.svg' },
      { i18nKey: 'explore', src: '/icons/search-line.svg' },
      { i18nKey: 'educate', src: '/icons/presentation.svg' }
    ] as const
  ).map(({ i18nKey, ...card }) => ({
    ...card,
    title: m[`home.usage.${i18nKey}.title`](),
    desc: m[`home.usage.${i18nKey}.desc`]()
  }))

  // FIXME i18n specific logos
  const localizedLogos = (
    {
      da: [],
      en: [],
      fr: [
        {
          class: 'max-h-[95px]',
          src: '/orgs/minicult.svg',
          alt: 'Ministère de la Culture',
          title: 'Ministère de la Culture'
        },
        {
          class: 'max-h-[95px] dark:invert',
          src: '/orgs/ateliernumerique.png',
          alt: 'Atelier numérique',
          title: 'Atelier numérique'
        }
      ],
      lt: [],
      se: []
    } satisfies Record<Locale, HTMLImgAttributes[]>
  )[locale]
</script>

<span class="text-primary"></span>

<main id="content" class="">
  <section class="fr-container--fluid bg-light-grey pb-13 lg:pt-18 pt-10 lg:pb-28">
    <div
      class="fr-container max-w-[1070px]! flex flex-col gap-20 md:flex-row md:items-center md:gap-0"
    >
      <div class="">
        <div class="mb-15 px-4 md:px-0">
          <div class="mb-10 max-w-[280px] md:w-[320px] md:max-w-[320px]">
            <h1 class="mb-5!">
              {@html sanitize(m['home.intro.title']({ props: 'class="text-primary"' }))}
            </h1>
            <p>{m['home.intro.desc']()}</p>
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
              {@html sanitize(
                m['home.intro.tos.accept']({
                  linkProps: propsToAttrs({ href: '/modalites', target: '_blank' })
                })
              )}
              <p class="fr-message">{m['home.intro.tos.help']()}</p>
            </label>
            <div
              class="fr-messages-group"
              id="checkbox-error-messages"
              aria-live="assertive"
              class:fr-hidden={!showError}
            >
              <p class="fr-message fr-message--error" id="checkbox-error-message-error">
                {m['home.intro.tos.error']()}
              </p>
            </div>
          </div>
        </div>

        <Button
          id="start_arena_btn"
          type="submit"
          text={m['header.startDiscussion']()}
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
      <h3 class="mb-3! text-center">{m['home.use.title']()}</h3>
      <p class="text-grey mb-8! text-center">{m['home.use.desc']()}</p>

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
          {@html sanitize(m['home.europe.title']({ props: 'class="text-primary"' }))}
        </h3>
        <p class="mb-2!">{m['home.europe.desc']()}</p>
        <p><strong class="block">{m['home.europe.question']()}</strong></p>

        <Link button size="lg" href="FIXME" text={m['actions.contactUs']()} />
      </div>

      <div
        class="py-15 flex w-full flex-col justify-center gap-8 rounded-xl bg-white px-9 xl:flex-row"
      >
        <img
          src="/home/comparia-stars.svg"
          aria-hidden="true"
          alt=""
          class="m-auto max-w-fit xl:m-0"
        />

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
        <h4 class="mb-2! text-center">{m['home.vote.title']()}</h4>
        <p class="text-grey text-center">{m['home.vote.desc']()}</p>

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
            text={m['home.vote.datasetAccess']()}
          />
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container--fluid bg-light-grey py-10 lg:py-20">
    <div class="fr-container">
      <h3 class="mb-2! text-center">{m['home.usage.title']()}</h3>
      <p class="text-grey fr-mb-4w text-center">{m['home.vote.desc']()}</p>

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
      <!-- i18n: specific to locales -->
      <div class="cg-border bg-white px-5 py-10 md:px-8">
        <h5>{m['home.origin.team.title']()}</h5>
        <p>{m['home.origin.team.desc']()}</p>

        <div class="mt-12 flex flex-wrap gap-8">
          {#each localizedLogos as logoProps}
            <img {...logoProps} />
          {/each}
        </div>
      </div>

      <div class="cg-border bg-white px-5 py-10 md:px-8">
        <h5>{m['home.origin.project.title']()}</h5>
        <p>
          {@html sanitize(
            m['home.origin.project.desc']({ linkProps: externalLinkProps('https://beta.gouv.fr') })
          )}
        </p>

        <div class="mt-12 flex flex-wrap gap-8">
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
      <h3 class="mb-8! lg:mb-10! text-center">{m['home.faq.title']()}</h3>

      <FAQContent />

      <div class="mt-8 text-center lg:mt-11">
        <Link button size="lg" href="/faq" text={m['home.faq.discover']()} />
      </div>
    </div>
  </section>

  {#if locale === 'fr'}
    <Newsletter />
  {/if}
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
