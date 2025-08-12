<script lang="ts">
  import { Button, CheckboxGroup } from '$components/dsfr'
  import ModelCard from '$lib/components/ModelCard.svelte'
  import SeoHead from '$lib/components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import { getModelsContext } from '$lib/models'

  const models = getModelsContext()

  const editorFilter = {
    id: 'editor',
    legend: 'Éditeur',
    options: [...new Set(models.map((m) => m.organisation))]
      .sort()
      .map((org) => ({ value: org, count: models.filter((m) => m.organisation === org).length }))
  }

  const sizeFilter = {
    id: 'size',
    legend: 'Taille (en milliards de paramètres)',
    options: [
      { value: 'XS', label: '< à 7 milliards' },
      { value: 'S', label: 'de 7 à 20 milliards' },
      { value: 'M', label: 'de 20 à 70 milliards' },
      { value: 'L', label: 'de 70 à 150 milliards' },
      { value: 'XL', label: '> 150 milliards' }
    ].map((option) => ({
      ...option,
      count: models.filter((m) => m.friendly_size === option.value).length
    }))
  }

  const licenseFilter = {
    id: 'license',
    legend: "Licence d'utilisation",
    options: [...new Set(models.map((m) => m.license))]
      .filter((l) => !l.toLowerCase().includes('propriétaire'))
      .map((license) => ({
        label: license as string,
        value: license as string,
        count: models.filter((m) => m.license === license).length
      }))
      .concat([
        {
          label: 'Commerciale',
          value: 'Propriétaire',
          count: models.filter((m) => m.license.toLowerCase().includes('propriétaire')).length
        }
      ])
  }

  let editors = $state([])
  let sizes = $state([])
  let licenses = $state([])
  let sortingMethod = $state<'name-asc' | 'date-desc' | 'params-asc' | 'org-asc'>('name-asc')
  const filteredModels = $derived(
    models
      .filter((model) => {
        const sizeMatch = sizes.length === 0 || sizes.includes(model.friendly_size)
        const orgMatch = editors.length === 0 || editors.includes(model.organisation)
        const licenseMatch =
          licenses.length === 0 ||
          licenses.some((selectedLicense) => {
            if (selectedLicense === 'Propriétaire') {
              return model.license.toLowerCase().includes('propriétaire')
            }
            return model.license === selectedLicense
          })
        return sizeMatch && orgMatch && licenseMatch
      })
      .sort((a, b) => {
        switch (sortingMethod) {
          case 'date-desc':
            if (a.release_date && b.release_date && a.release_date !== b.release_date) {
              // @ts-ignore
              return new Date('01/' + b.release_date) - new Date('01/' + a.release_date)
            } else if (a.release_date) {
              return -1
            } else if (b.release_date) {
              return 1
            }
          case 'params-asc':
            if (a.params && b.params && a.params !== b.params) {
              return a.params - b.params
            }
          case 'org-asc':
            return a.organisation.localeCompare(b.organisation)
          default:
            return a.simple_name.localeCompare(b.simple_name)
        }
      })
  )

  const allFilter = $derived([editors, sizes, licenses])
  const filterCount = $derived(allFilter.reduce((acc, f) => acc + (f.length ? 1 : 0), 0))

  function resetFilters(e: MouseEvent) {
    e.preventDefault()
    allFilter.forEach((arr) => (arr.length = 0))
  }
</script>

<SeoHead title={m['seo.titles.modeles']()} />

<main>
  <div class="fr-container pb-10 md:flex md:flex-row md:py-10">
    <aside
      class="fr-sidemenu mb-5 md:mb-0 md:basis-1/3"
      role="navigation"
      aria-labelledby="sidemenu-title"
    >
      <div class="fr-sidemenu__inner h-full">
        <button
          id="results-count"
          aria-expanded="true"
          aria-controls="fr-modal-filters-section"
          type="button"
          class="fr-sidemenu__btn"
        >
          Afficher les filtres
          {#if filterCount}
            <span class="fr-badge bg-primary! fr-badge--sm rounded-full! ms-2 text-white">
              {filterCount}
            </span>
          {/if}
        </button>
        <div class="fr-collapse" id="fr-modal-filters-section">
          <p class="fr-h5 mb-5! hidden md:block">
            {models.length}
            {models.length === 1 ? 'modèle' : 'modèles'}
          </p>
          <form class="mt-8 md:mt-0">
            <CheckboxGroup
              {...editorFilter}
              bind:value={editors}
              legendClass="fr-h6"
              labelClass="flex-nowrap!"
              class="border-b-1! border-(--grey-925-125)! pb-6! mb-8! md:border-0! md:mb-0!"
            >
              {#snippet labelSlot({ option })}
                <div class="me-2">{option.value}</div>
                <div class="text-(--grey-625-425) ms-auto text-sm">{option.count}</div>
              {/snippet}
            </CheckboxGroup>

            <CheckboxGroup
              {...sizeFilter}
              bind:value={sizes}
              legendClass="fr-h6"
              labelClass="flex-nowrap!"
              class="border-b-1! border-(--grey-925-125)! pb-6! mb-8! md:border-0! md:mb-0!"
            >
              {#snippet labelSlot({ option })}
                <div class="me-2"><strong>{option.value} :</strong> {option.label}</div>
                <div class="text-(--grey-625-425) ms-auto text-sm">{option.count}</div>
              {/snippet}
            </CheckboxGroup>

            <CheckboxGroup
              {...licenseFilter}
              bind:value={licenses}
              legendClass="fr-h6"
              labelClass="flex-nowrap!"
            >
              {#snippet labelSlot({ option })}
                <div class="me-2">{option.label}</div>
                <div class="text-(--grey-625-425) ms-auto text-sm">{option.count}</div>
              {/snippet}
            </CheckboxGroup>

            <div class="mb-8">
              <Button text="Réinitialiser" variant="tertiary-no-outline" onclick={resetFilters} />
            </div>
          </form>
        </div>
      </div>
    </aside>

    <div class="basis-full">
      <!-- <h2 class="fr-h2">{m['models.title']()}</h2>
      <p class="fr-text--lead">{m['models.intro']()}</p> -->

      <p class="fr-h6 mb-4! md:hidden">
        {models.length}
        {models.length === 1 ? 'modèle' : 'modèles'}
      </p>

      <div class="fr-select-group">
        <label class="fr-label" for="model-order">Trier par</label>
        <select
          class="fr-select w-auto!"
          id="model-order"
          bind:value={sortingMethod}
          name="model-order"
        >
          <option value="name-asc">Nom du modèle (A à Z)</option>
          <option value="date-desc">Date de sortie (du plus au moins récent)</option>
          <option value="params-asc">Taille (du plus petit au plus grand)</option>
          <option value="org-asc">Éditeur (A à Z)</option>
        </select>
      </div>

      <div class="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        {#each filteredModels as model (model.id)}
          <ModelCard {model} />
        {/each}
      </div>

      {#if filteredModels.length === 0}
        <p class="fr-text--lead fr-mt-4w">{m['models.noresults']()}</p>
      {/if}
    </div>
  </div>
</main>
