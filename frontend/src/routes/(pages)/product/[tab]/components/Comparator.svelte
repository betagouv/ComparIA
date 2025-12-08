<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import { getI18nContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { sanitize } from '$lib/utils/commons'

  const locale = getLocale()
  const i18nData = getI18nContext()

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

  const availableImgsLocales = ['da', 'sv', 'fr']
  const chatbotScreenshotSrc = $derived(
    `/product/chatbot-screenshot-${availableImgsLocales.includes(locale) ? locale : 'en'}.png`
  )
</script>

<div class="pb-4">
  <div class="gap-10 lg:flex-row lg:gap-20 flex flex-col items-center">
    <div class="md:basis-1/3">
      <h2 class="fr-h3 leading-11!">
        {@html sanitize(m['product.comparator.title']({ props: 'class="text-primary"' }))}
      </h2>

      <Link
        button
        href="/arene"
        text={m['product.comparator.cta']()}
        class="sm:w-auto! lg:mt-13 w-full!"
      />
    </div>

    <div class="p-4 rounded-[28px] bg-[#686868]">
      <img
        src={chatbotScreenshotSrc}
        alt={m['product.comparator.screenshotAlt']()}
        class="rounded-2xl w-full max-w-[622px]"
      />
    </div>
  </div>

  <div class="py-15 lg:py-20">
    <h3 class="fr-h4 md:text-center">{m['product.comparator.challenges.title']()}</h3>

    <div class="mt-10 gap-6 md:grid-cols-2 xl:grid-cols-4 grid">
      {#each challengesCards as card, i (i)}
        <div class="cg-border px-4 py-5 md:px-8 md:py-6">
          <Icon icon={card.icon} block class={card.class + ' mb-5'} />
          <h4 class="fr-h6 mb-3!">{card.title}</h4>
          <p class="fr-message text-sm!">{card.desc}</p>
        </div>
      {/each}
    </div>
  </div>

  <div class="cg-border bg-light-grey gap-10 px-4 py-10 md:grid-cols-2 grid">
    <div class="flex">
      <img
        src="/product/comparia-europe.png"
        aria-hidden="true"
        alt=""
        width="326px"
        class="m-auto"
      />
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

      <Link
        button
        href="mailto:{i18nData.contact}"
        text={m['actions.contactUs']()}
        class="sm:w-auto! w-full!"
      />
    </div>
  </div>
</div>
