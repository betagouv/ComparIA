<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import InfoCard from '$components/InfoCard.svelte'
  import OpennessScore from '$components/OpennessScore.svelte'
  import { m } from '$lib/i18n/messages'
  import type { BotModel, Commons } from '$lib/models'
  import { getModelCards } from '$lib/models'

  let {
    model,
    commons,
    onModelSelected,
    modalId
  }: {
    model: BotModel
    commons: Commons
    onModelSelected: (name: string) => void
    modalId: string
  } = $props()

  const cards = $derived.by(() => {
    if (!model) return []
    const cards = getModelCards(model, 'xs', commons)
    return [cards.size, cards.license, cards.release, cards.energy, cards.sovereignty, cards.rank]
  })
</script>

<article
  class={[
    'fr-card fr-enlarge-link cg-border rounded-xl bg-very-light-grey! bg-none!',
    { 'border-primary!': model.new }
  ]}
>
  <div class="fr-card__body">
    <div class="fr-card__content px-3! pt-3!">
      <h3
        class="fr-card__title fr-text--sm mb-4! leading-normal! font-normal! text-dark-grey gap-2 flex items-center text-[14px]!"
      >
        <AILogo logo={model.lab.logo} alt={model.lab.name} />
        <div>
          {model.lab.name}/<a
            class="text-black! after:text-primary"
            data-fr-opened="false"
            aria-controls={modalId}
            href="#{model.id}"
            onclick={() => onModelSelected(model.id)}
            ><span class="font-extrabold">{model.name}</span></a
          >
        </div>
      </h3>

      <!-- Not a <dl>: InfoCard wraps its own markup around the label, so the
           dt/dd never end up direct children and the list is invalid. -->
      <div class="fr-card__desc p-0 gap-2 mt-0! sm:grid-cols-3 grid grid-cols-2">
        {#each cards as card (card.id)}
          <!-- id after the spread and scoped to the model: getModelCards hands
               out the same 'size'/'license'/... ids to every card, and this
               page renders one set per model. Left alone, every tooltip on the
               list points at the first model's text. -->
          {#if card.id === 'sovereignty'}
            <InfoCard
              {...card}
              id="{model.id}-{card.id}"
              rootTag="div"
              content={undefined}
              size="xxs"
              titleTag="p"
              contentTag="div"
            >
              <OpennessScore {model} detailed />
            </InfoCard>
          {:else}
            <InfoCard
              {...card}
              id="{model.id}-{card.id}"
              rootTag="div"
              size="xxs"
              titleTag="p"
              contentTag="div"
            />
          {/if}
        {/each}
      </div>

      <div class="fr-card__start m-0! order-2!">
        <ul class="fr-badges-group">
          {#if model.status === 'archived' || model.new}
            <li
              class={[
                'px-4! py-1! left-4 font-bold absolute bottom-[1.75rem] rounded-[3.75rem] text-[14px]',
                model.new ? 'bg-primary text-white' : 'text-dark-grey bg-[--grey-900-175]'
              ]}
            >
              {m[model.new ? 'words.new' : 'words.archived']()}
            </li>
          {/if}
        </ul>
      </div>
    </div>
  </div>
</article>
