<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { m } from '$lib/i18n/messages'
  import type { BotModel } from '$lib/models'
  import { sanitize } from '$lib/utils/commons'
  import { Badge } from './dsfr'

  let {
    model,
    onModelSelected,
    modalId
  }: {
    model: BotModel
    onModelSelected: (name: string) => void
    modalId: string
  } = $props()

  const { license, releaseDate, size } = model.badges
  const badges = [license, releaseDate, size].filter((b) => !!b)
</script>

<div
  class={[
    'fr-card fr-enlarge-link cg-border rounded-xl bg-none!',
    { 'border-primary!': model.new }
  ]}
>
  <div class="fr-card__body">
    <div class="fr-card__content px-5! md:px-4! md:pt-4!">
      <h6
        class="fr-card__title text-dark-grey mb-3! flex items-center gap-3 text-[14px]! leading-normal! font-normal!"
      >
        <AILogo iconPath={model.icon_path} alt={model.organisation} />
        <div>
          {model.organisation}/<a
            class="after:text-primary text-black!"
            data-fr-opened="false"
            aria-controls={modalId}
            href="#{model.id}"
            onclick={() => onModelSelected(model.id)}
            ><span class="font-extrabold">{model.simple_name}</span></a
          >
        </div>
      </h6>

      <div class="fr-card__desc">
        {@html sanitize(model.desc).replaceAll('<p>', '<p class="last:mb-0!">')}
      </div>

      <div class="fr-card__start order-2!">
        <ul class="fr-badges-group">
          {#if model.status === 'archived' || model.new}
            <li
              class={[
                'absolute bottom-[1.75rem] rounded-[3.75rem] px-4! py-1! text-[14px] font-bold',
                model.new ? 'bg-primary text-white' : 'text-dark-grey bg-(--grey-900-175)'
              ]}
            >
              {m[model.new ? 'words.new' : 'words.archived']()}
            </li>
          {/if}
          {#each badges as badge, i}
            <li><Badge id="card-badge-{i}" size="xs" {...badge} noTooltip /></li>
          {/each}
        </ul>
      </div>
    </div>
  </div>
</div>
