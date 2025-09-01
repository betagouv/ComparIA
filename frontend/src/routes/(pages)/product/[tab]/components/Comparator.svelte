<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { sanitize } from '$lib/utils/commons'

  const locale = getLocale()

  const challengesCards = (
    [
      { i18nKey: 'bias', icon: 'old-globe', class: 'text-yellow' },
      { i18nKey: 'impacts', icon: 'leaf-line', class: 'text-green' },
      { i18nKey: 'pluralism', icon: 'plural', class: 'text-primary' },
      { i18nKey: 'thinking', icon: 'chat-charts', class: 'text-red' }
    ] as const
  ).map(({ i18nKey, ...card }) => ({
    ...card,
    title: m[`product.comparator.challenges.${i18nKey}.title`](),
    desc: m[`product.comparator.challenges.${i18nKey}.desc`]()
  }))

  const chatbotScreenshotSrc = $derived(
    `/product/chatbot-screenshot-${locale === 'fr' ? 'fr' : 'en'}.png`
  )
</script>

<div class="pb-4">
  <div class="flex flex-col items-center gap-10 lg:flex-row lg:gap-20">
    <div class="md:basis-1/3">
      <h2 class="fr-h3">
        {@html sanitize(m['product.comparator.title']({ props: 'class="text-primary"' }))}
      </h2>

      <Link button href="/arene" text={m['product.comparator.cta']()} class="lg:mt-13" />
    </div>

    <div class="rounded-[28px] bg-[#686868] p-4">
      <img src={chatbotScreenshotSrc} class="w-full max-w-[622px] rounded-2xl" />
    </div>
  </div>

  <div class="py-15 lg:py-20">
    <h3 class="fr-h4 md:text-center">{m['product.comparator.challenges.title']()}</h3>

    <div class="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
      {#each challengesCards as card}
        <div class="cg-border px-4 py-5 md:px-8 md:py-6">
          <Icon icon={card.icon} block class={card.class + ' mb-5'} />
          <h4 class="fr-h6 mb-3!">{card.title}</h4>
          <p class="fr-message text-sm!">{card.desc}</p>
        </div>
      {/each}
    </div>
  </div>

  <div class="cg-border bg-light-grey grid gap-10 px-4 py-10 md:grid-cols-2">
    <div class="flex">
      <!-- FIXME replace image -->
      <img src="/home/comparia-stars.svg" aria-hidden="true" alt="" width="326px" class="m-auto" />
    </div>

    <div class="lg:pe-17">
      <h3 class="fr-h4">
        {@html sanitize(m['product.comparator.europe.title']({ props: 'class="text-primary"' }))}
      </h3>
      <p>
        <strong>{m['product.comparator.europe.adventure']()}</strong>
        {m['product.comparator.europe.desc']()}
      </p>
      <p><strong>{m['product.comparator.europe.catch']()}</strong></p>

      <Link button href="mailto:contact@comparia.beta.gouv.fr" text={m['actions.contactUs']()} />
    </div>
  </div>
</div>
