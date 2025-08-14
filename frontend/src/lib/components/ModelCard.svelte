<script lang="ts">
  import type { APIBotModel } from '$lib/models'

  let {
    model,
    onModelSelected,
    modalId
  }: {
    model: APIBotModel
    onModelSelected: (name: string) => void
    modalId: string
  } = $props()

  const badges = [
    model.fully_open_source
      ? { color: 'green-emeraude', text: 'Open source' }
      : model.distribution === 'open-weights'
        ? { color: 'yellow-tournesol', text: 'Semi-ouvert' }
        : { color: 'orange-terre-battue', text: 'Propriétaire' },
    model.release_date ? { color: '', text: `Sortie ${model.release_date}` } : null,
    {
      color: 'info',
      text:
        model.distribution === 'open-weights'
          ? `${Math.round(model.params)} mds de paramètres`
          : `Taille estimée (${model.friendly_size})`
    }
  ].filter((b) => !!b)
</script>

<div class="fr-card fr-enlarge-link cg-border bg-none! rounded-xl">
  <div class="fr-card__body">
    <div class="fr-card__content px-5! md:px-4! md:pt-4!">
      <h6 class="fr-card__title text-dark-grey font-normal! text-sm! mb-3! flex items-start gap-3">
        <img
          class="object-contain"
          src="/orgs/{model.icon_path}"
          width="20"
          alt="{model.organisation} logo"
        />
        <div>
          {model.organisation}/<a
            class="text-black! after:text-primary"
            data-fr-opened="false"
            aria-controls={modalId}
            href="#{model.id}"
            onclick={() => onModelSelected(model.id)}
            ><span class="font-extrabold">{model.simple_name}</span></a
          >
        </div>
      </h6>

      <p class="fr-card__desc">{model.excerpt}</p>

      <div class="fr-card__start order-2!">
        <ul class="fr-badges-group">
          {#each badges as badge}
            <li>
              <p class={`text-xs! fr-badge fr-badge--${badge.color} fr-badge--no-icon`}>
                {badge.text}
              </p>
            </li>
          {/each}
        </ul>
      </div>
    </div>
  </div>
  <div class="fr-card__header"></div>
</div>
