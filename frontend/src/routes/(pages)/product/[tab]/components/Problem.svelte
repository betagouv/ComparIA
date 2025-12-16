<script lang="ts">
  import { Icon } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'

  const diversityCards = (['stereotypes', 'english', 'diversity'] as const).map((i18nKey) => ({
    title: m[`product.problem.diversity.${i18nKey}.title`](),
    desc: m[`product.problem.diversity.${i18nKey}.desc`]()
  }))

  const alignmentCards = [
    {
      icon: 'i-ri-chat-voice-ai-line',
      class: 'text-green',
      title: m['product.problem.alignment.alignment.title'](),
      ps: (['a', 'b', 'c'] as const).map((p) => m[`product.problem.alignment.alignment.${p}`]())
    },
    {
      icon: 'i-ri-database-line',
      class: 'text-primary',
      title: m['product.problem.alignment.datasets.title'](),
      ps: (['a', 'b', 'c'] as const).map((p) => m[`product.problem.alignment.datasets.${p}`]())
    },
    {
      icon: 'i-ri-translate-2',
      class: 'text-orange',
      title: m['product.problem.alignment.english.title'](),
      ps: (['a', 'b', 'c'] as const).map((p) => m[`product.problem.alignment.english.${p}`]())
    },
    {
      icon: 'i-ri-question-answer-line',
      class: 'text-yellow',
      title: m['product.problem.alignment.diversity.title'](),
      ps: (['a', 'b', 'c', 'd'] as const).map((p) =>
        m[`product.problem.alignment.diversity.${p}`]()
      )
    }
  ] as const
</script>

<div class="py-10">
  <div class="gap-6 md:grid-cols-2 xl:grid-cols-4 grid">
    <h2 class="fr-h3 mb-3! leading-11!">
      {@html sanitize(m['product.problem.title']({ props: 'class="text-orange"' }))}
    </h2>

    {#each diversityCards as card, i (i)}
      <section class="cg-border p-5">
        <h3 class="mb-3! text-base!">{card.title}</h3>
        <p class="text-sm! text-start!">{card.desc}</p>
      </section>
    {/each}
  </div>

  <div class="mt-17">
    <h3 class="fr-h5 text-primary! text-center">{m['product.problem.alignment.title']()}</h3>
    <p class="fr-h5 text-center!">{m['product.problem.alignment.desc']()}</p>
  </div>

  <div class="mt-12 gap-6 md:grid-cols-2 grid">
    {#each alignmentCards as card, i (i)}
      <section class="cg-border bg-very-light-grey px-5 py-6">
        <Icon icon={card.icon} block class={card.class + ' mb-3'} />
        <h4 class="fr-h6 mb-3!">{card.title}</h4>

        {#each card.ps as p, j (j)}
          <p class="mb-3! leading-normal! text-[12px]!">{@html sanitize(p)}</p>
        {/each}
      </section>
    {/each}
  </div>
</div>
