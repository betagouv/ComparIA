<script lang="ts">
  import ModelCard from '$lib/components/ModelCard.svelte'
  import ModelFilters from '$lib/components/ModelFilters.svelte'
  import SeoHead from '$lib/components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import { getModelsContext } from '$lib/models'

  const models = getModelsContext()

  let selectedSizes = $state<string[]>([])
  let selectedOrgs = $state<string[]>([])
  let selectedLicenses = $state<string[]>([])

  const filteredModels = $derived(
    models.filter((model) => {
      const sizeMatch = selectedSizes.length === 0 || selectedSizes.includes(model.friendly_size)
      const orgMatch = selectedOrgs.length === 0 || selectedOrgs.includes(model.organisation)
      const licenseMatch =
        selectedLicenses.length === 0 ||
        selectedLicenses.some((selectedLicense) => {
          if (selectedLicense === 'Propriétaire') {
            return model.license.toLowerCase().includes('propriétaire')
          }
          return model.license === selectedLicense
        })
      return sizeMatch && orgMatch && licenseMatch
    })
  )

  function handleFiltersChange(event: CustomEvent) {
    selectedSizes = event.detail.sizes
    selectedOrgs = event.detail.orgs
    selectedLicenses = event.detail.licenses
  }

  function handleResetFilters() {
    selectedSizes = []
    selectedOrgs = []
    selectedLicenses = []
  }
</script>

<SeoHead title={m['seo.titles.modeles']()} />

<div class="fr-container fr-py-4w">
  <div class="fr-grid-row fr-grid-row--gutters">
    <div class="fr-col-12 fr-col-md-3">
      <ModelFilters
        {models}
        bind:selectedSizes
        bind:selectedOrgs
        bind:selectedLicenses
        on:filtersChange={handleFiltersChange}
        on:reset={handleResetFilters}
      />
    </div>
    <div class="fr-col-12 fr-col-md-9">
      <h2 class="fr-h2">{m['models.title']()}</h2>
      <p class="fr-text--lead">{m['models.intro']()}</p>

      <div class="models-grid">
        {#each filteredModels as model (model.id)}
          <ModelCard {model} />
        {/each}
      </div>

      {#if filteredModels.length === 0}
        <p class="fr-text--lead fr-mt-4w">{m['models.noResults']()}</p>
      {/if}
    </div>
  </div>
</div>

<style>
  .models-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1.5rem;
  }
</style>
