<script lang="ts">
  import { Accordion, AccordionGroup, Button, Icon, Link } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'

  const publicCards = (
    [
      { i18nKey: '1', icon: 'school-line', variant: 'text-yellow' },
      { i18nKey: '2', icon: 'university', variant: 'text-red' },
      { i18nKey: '3', icon: 'association', variant: 'text-green' },
      { i18nKey: '4', icon: 'building-4-line', variant: 'text-primary' }
    ] as const
  ).map(({ i18nKey, ...card }) => ({
    ...card,
    title: m[`duel.3.cards.${i18nKey}.title`](),
    desc: m[`duel.3.cards.${i18nKey}.desc`]()
  }))
</script>

<main>
  <section class="fr-container--fluid bg-very-light-grey py-15">
    <div class="fr-container">
      <div class="grid gap-10 md:grid-cols-2 lg:px-20">
        <div class="my-auto md:max-w-[415px]">
          <h1 class="mb-3! fr-h2">
            {@html sanitize(m['duel.1.title']({ props: 'class="text-primary"' }))}
          </h1>
          <p class="mb-7! md:text-lg">{@html sanitize(m['duel.1.desc']())}</p>

          <Link
            button
            href="https://comparia.getgrist.com/forms/h2i36mSYhJsAyb5r4Bee5c/29"
            text={m['duel.1.cta']()}
            size="lg"
            class="w-full!"
          />
        </div>

        <div class="my-auto">
          <img src="/duel/workshop.jpg" class="fr-responsive-img rounded-xl shadow-md" />
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container--fluid bg-light-grey py-15">
    <div class="fr-container">
      <div class="grid gap-10 md:grid-cols-2 lg:px-20">
        <h2 class="fr-h4 my-auto! leading-[1.875]! md:max-w-[460px]">
          {@html sanitize(m['duel.2.title']({ props: 'class="text-primary"' }))}
        </h2>

        <ul class="p-0! m-0! md:ms-auto! my-auto">
          {#each ['1', '2', '3', '4'] as const as i (i)}
            <li class="not-last:mb-4 p-0! list-none md:text-lg">
              <Icon icon="checkbox-line" class="text-primary" />
              {m[`duel.2.list.${i}`]()}
            </li>
          {/each}
        </ul>
      </div>
    </div>
  </section>

  <section class="fr-container--fluid bg-very-light-grey py-15">
    <div class="fr-container">
      <div class="lg:px-10">
        <div class="mb-6 text-center">
          <h2 class="fr-h3 mb-3!">{m['duel.3.title']()}</h2>
          <p class="text-grey mb-0!">{m['duel.3.desc']()}</p>
        </div>

        <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {#each publicCards as card}
            <div class="cg-border bg-white p-4 md:px-7 md:py-6">
              <Icon icon={card.icon} class={card.variant} size="lg" block />
              <h3 class="text-lg! my-3! md:mt-5!">{card.title}</h3>
              <p class="text-grey text-sm!">{card.desc}</p>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container--fluid bg-light-grey py-13">
    <div class="fr-container">
      <div class="lg:px-10">
        <div class="mb-11 text-center">
          <h2 class="fr-h3 mb-3! text-primary!">{m['duel.4.title']()}</h2>
          <p class="text-grey mb-0!">{m['duel.4.desc']()}</p>
        </div>

        <div class="gap-x-15 grid gap-y-10 md:grid-cols-2 md:gap-y-20 lg:grid-cols-3">
          {#each ['1', '2', '3', '4', '5', '6'] as const as i}
            <div class="flex items-start gap-2">
              <div class="mt-1 flex items-end gap-1">
                <div class="bg-primary h-[11px] w-[11px] rounded-full"></div>
                <span class="text-primary text-[40px] font-bold">{i}</span>
              </div>
              <div>
                <h3 class="fr-h6 mb-1!">{m[`duel.4.list.${i}.title`]()}</h3>
                <p class="mb-0!"><em>{m[`duel.4.list.${i}.duration`]()}</em></p>
                <p class="text-grey mb-0! leading-[1.7]!">{m[`duel.4.list.${i}.desc`]()}</p>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container--fluid bg-very-light-grey py-18">
    <div class="fr-container">
      <div class="grid gap-10 md:grid-cols-2 lg:px-12">
        <div class="my-auto md:max-w-[440px]">
          <h2 class="mb-6!">{m['duel.5.title']()}</h2>

          <ul class="p-0! m-0! mb-13!">
            {#each ['1', '2', '3', '4'] as const as i (i)}
              <li class="not-last:mb-3 p-0! list-none md:text-lg">
                <Icon icon="checkbox-line" class="text-primary" />
                {m[`duel.5.list.${i}`]()}
              </li>
            {/each}
          </ul>

          <Link
            button
            href="https://comparia.getgrist.com/forms/h2i36mSYhJsAyb5r4Bee5c/29"
            text={m['duel.5.cta']()}
            size="lg"
          />
        </div>

        <div class="my-auto">
          <img src="/duel/extension.png" class="fr-responsive-img rounded-xl shadow-md" />
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container--fluid py-15 bg-white">
    <div class="fr-container">
      <div class="lg:px-24">
        <h2 class="fr-h3 mb-8! lg:mb-10! text-center">{m['duel.6.title']()}</h2>

        <AccordionGroup>
          {#each ['1', '2', '3'] as const as i}
            <Accordion id={`faq-${i}`} label={m[`duel.6.questions.${i}.title`]()}>
              {m[`duel.6.questions.${i}.desc`]()}
            </Accordion>
          {/each}
        </AccordionGroup>

        <div class="mt-8 text-center lg:mt-11">
          <Link
            button
            size="lg"
            href="mailto:simonas.zilinskas@beta.gouv.fr"
            text={m['duel.6.cta']()}
          />
        </div>
      </div>
    </div>
  </section>
</main>
