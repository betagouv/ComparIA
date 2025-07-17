<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { Model } from '$lib/types'

  export let model: Model

  $: isProprietary = model.license.toLowerCase().includes('propriétaire')
  $: badgeColor = model.fully_open_source
    ? 'green-emeraude'
    : model.distribution === 'open-weights'
      ? 'yellow-tournesol'
      : 'orange-terre-battue'

  $: badgeText = model.fully_open_source
    ? 'Open source'
    : model.distribution === 'open-weights'
      ? 'Semi-ouvert'
      : 'Propriétaire'
</script>

<div class="fr-card fr-enlarge-link">
  <div class="fr-card__body">
    <div class="fr-card__content">
      <h6 class="fr-card__title">
        <a href="#" data-fr-opened="false" aria-controls="fr-modal-{model.id}"></a>
      </h6>
      <h6 class="fr-mb-2w github-title">
        <img
          class="fr-mt-n2v relative"
          src="assets/orgs/{model.icon_path}"
          width="34"
          alt="{model.organisation} logo"
        />
        {model.organisation}/<strong>{model.simple_name}</strong>
      </h6>
      <p class="fr-mb-4w">
        <span
          class="fr-badge fr-badge--sm fr-badge--{badgeColor} fr-badge--no-icon fr-mr-1v fr-mb-1v"
        >
          {badgeText}
        </span>
        {#if model.release_date}
          <span class="fr-badge fr-badge--sm fr-badge--no-icon fr-mr-1v">
            Sortie {model.release_date}
          </span>
        {/if}
        <span class="fr-badge fr-badge--sm fr-badge--info fr-badge--no-icon fr-mr-1v fr-mb-1v">
          {#if model.distribution === 'open-weights'}
            {Math.round(model.params)} mds de paramètres&nbsp;
            <a
              class="fr-icon fr-icon--xs fr-icon--question-line"
              aria-describedby="params-{model.id}"
            ></a>
          {:else}
            Taille estimée ({model.friendly_size})
          {/if}
        </span>
      </p>
      <p class="fr-card__desc">{model.excerpt}</p>
    </div>
  </div>
</div>

<style>
  .github-title {
    color: var(--text-default-grey) !important;
    font-weight: 400 !important;
    font-size: 1.1rem;
  }

  .github-title img {
    vertical-align: middle;
  }

  .relative {
    position: relative;
  }
</style>
