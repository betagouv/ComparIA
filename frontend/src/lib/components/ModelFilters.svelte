<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import type { Model } from '$lib/types'

  export let models: Model[] = []
  export let selectedSizes: string[] = []
  export let selectedOrgs: string[] = []
  export let selectedLicenses: string[] = []

  const dispatch = createEventDispatcher()

  $: orgs = [...new Set(models.map((m) => m.organisation))].sort()
  $: sizes = ['XS', 'S', 'M', 'L', 'XL']
  $: sizeDescriptions = {
    XS: '< à 7 milliards',
    S: 'de 7 à 20 milliards',
    M: 'de 20 à 70 milliards',
    L: 'de 70 à 150 milliards',
    XL: '> 150 milliards'
  }

  $: licenses = [...new Set(models.map((m) => m.license))].filter(
    (l) => !l.toLowerCase().includes('propriétaire')
  )
  $: proprietaryLicenses = [...new Set(models.map((m) => m.license))].filter((l) =>
    l.toLowerCase().includes('propriétaire')
  )

  function handleFilterChange() {
    dispatch('filtersChange', {
      sizes: selectedSizes,
      orgs: selectedOrgs,
      licenses: selectedLicenses
    })
  }

  function resetFilters() {
    selectedSizes = []
    selectedOrgs = []
    selectedLicenses = []
    dispatch('reset')
  }

  function getCount(filterType: string, value: string) {
    switch (filterType) {
      case 'size':
        return models.filter((m) => m.friendly_size === value).length
      case 'org':
        return models.filter((m) => m.organisation === value).length
      case 'license':
        return models.filter((m) => {
          const isProprietary = m.license.toLowerCase().includes('propriétaire')
          return isProprietary ? value === 'Propriétaire' : m.license === value
        }).length
      default:
        return 0
    }
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_to_interactive_role -->
<aside
  aria-labelledby="fr-modal-filters"
  role="dialog"
  id="fr-modal-filters-section"
  class="fr-modal fr-col-md-3 fr-pl-md-2w"
>
  <div class="fr-container--fluid modal-filters-content">
    <div class="fr-container fr-pl-4w">
      <h4 id="models-count" aria-live="polite">
        {models.length}
        {models.length === 1 ? 'modèle' : 'modèles'}
      </h4>
      <div>
        <button
          class="right fr-btn purple-btn fr-mb-4w md-hidden"
          title="Voir les résultats"
          id="results-count"
          aria-controls="fr-modal-filters-section"
        >
          Voir les {models.length}
          {models.length === 1 ? 'résultat' : 'résultats'}
        </button>
      </div>

      <form id="model-filter-form">
        <!-- Size Filter -->
        <h3 class="fr-accordion__title">
          <button
            type="button"
            class="fr-accordion__btn fr-h6"
            aria-expanded="true"
            aria-controls="accordion-size"
          >
            Taille (paramètres)
          </button>
        </h3>
        <div id="accordion-size" class="fr-collapse fr-checkbox-group fr-checkbox-group--sm">
          {#each sizes as size}
            <div class="fr-checkbox">
              <input
                type="checkbox"
                id="size-{size}"
                name="param-filter"
                value={size}
                bind:group={selectedSizes}
                on:change={handleFilterChange}
              />
              <label for="size-{size}">
                <strong>{size}&nbsp;:&nbsp;</strong>
                {sizeDescriptions[size]}
                <span class="filter-number">{getCount('size', size)}</span>
              </label>
            </div>
          {/each}
        </div>

        <!-- Organization Filter -->
        <h3 class="fr-accordion__title">
          <button
            type="button"
            class="fr-accordion__btn fr-h6"
            aria-expanded="false"
            aria-controls="accordion-orgs"
          >
            Éditeur
          </button>
        </h3>
        <div id="accordion-orgs" class="fr-collapse fr-checkbox-group fr-checkbox-group--sm">
          {#each orgs as org}
            <div class="fr-checkbox">
              <input
                type="checkbox"
                id="org-{org}"
                name="org-filter"
                value={org}
                bind:group={selectedOrgs}
                on:change={handleFilterChange}
              />
              <label for="org-{org}">
                {org}
                <span class="filter-number">{getCount('org', org)}</span>
              </label>
            </div>
          {/each}
        </div>

        <!-- License Filter -->
        <h3 class="fr-accordion__title">
          <button
            type="button"
            class="fr-accordion__btn fr-h6"
            aria-expanded="false"
            aria-controls="accordion-license"
          >
            Licence d'utilisation
          </button>
        </h3>
        <div
          id="accordion-license"
          class="fr-collapse fr-checkbox-group fr-checkbox-group--sm licenses-checkboxes"
        >
          {#each licenses as license}
            <div class="fr-checkbox">
              <input
                type="checkbox"
                id="license-{license}"
                name="license-filter"
                value={license}
                bind:group={selectedLicenses}
                on:change={handleFilterChange}
              />
              <label for="license-{license}">
                {license}
                <span class="filter-number">{getCount('license', license)}</span>
              </label>
            </div>
          {/each}
          {#if proprietaryLicenses.length > 0}
            <div class="fr-checkbox">
              <input
                type="checkbox"
                id="license-proprietaire"
                name="license-filter"
                value="Propriétaire"
                bind:group={selectedLicenses}
                on:change={handleFilterChange}
              />
              <label for="license-proprietaire">
                <strong>Commerciale</strong>
                <span class="filter-number">
                  {models.filter((m) => m.license.toLowerCase().includes('propriétaire')).length}
                </span>
              </label>
            </div>
          {/if}
        </div>
      </form>

      <a
        role="button"
        tabindex="0"
        id="reset-filters-link"
        class="fr-my-2w"
        on:click={resetFilters}
      >
        Réinitialiser
      </a>
    </div>
  </div>
</aside>

<style>
  .filter-number {
    color: #666666;
    background-color: white;
    border-radius: 50%;
    text-align: center;
    min-width: 24px;
    min-height: 24px;
    font-size: 0.9em;
    position: absolute;
    right: 2em;
  }

  .fr-checkbox-group {
    width: 100%;
  }

  .fr-checkbox {
    margin: 0.6em 0;
  }

  .fr-checkbox strong {
    font-weight: 600;
  }

  .licenses-checkboxes strong {
    font-weight: 500;
  }
</style>
