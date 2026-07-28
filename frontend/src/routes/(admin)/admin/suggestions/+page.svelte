<script lang="ts">
  import { goto, invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Badge, Button, Icon, Modal, Pagination, Select, Table } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api, type ApiError } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { TableCol } from '$lib/utils/data'
  import { toSearchString } from '$lib/utils/data'
  import { SvelteURLSearchParams } from 'svelte/reactivity'
  import CategoryIconPicker from './CategoryIconPicker.svelte'
  import CategoryManager from './CategoryManager.svelte'
  import type { PageProps } from './$types'
  import type { PromptSuggestion, SuggestionStatus } from './types'

  let { data }: PageProps = $props()

  const refetch = () => invalidate('admin:suggestions')
  const baseRoute = '/admin/suggestions'

  // These local controls are deliberately initialized from the SSR-loaded data,
  // then resynchronized below whenever SvelteKit refreshes the page data.
  // svelte-ignore state_referenced_locally
  let search = $state(data.filters.search)
  // svelte-ignore state_referenced_locally
  let status = $state(data.filters.status)
  // svelte-ignore state_referenced_locally
  let locale = $state(data.filters.locale)
  // svelte-ignore state_referenced_locally
  let categoryId = $state(data.filters.category_id)
  // svelte-ignore state_referenced_locally
  let currentPage = $state(data.suggestions.page - 1)

  let suggestionToToggle = $state<PromptSuggestion | null>(null)
  let actionLoading = $state(false)
  let prompt = $state('')
  let promptCategoryId = $state('')
  let promptLocale = $state('fr')
  let formError = $state<string>()
  let formLoading = $state(false)
  let categoryLocale = $state('fr')
  let categoryTitle = $state('')
  let categoryDescription = $state('')
  let categoryIcon = $state('i-ri-lightbulb-line')
  let categoryTooltip = $state('')
  let categoryFormError = $state<string>()
  let categoryFormLoading = $state(false)

  const categories = $derived(data.suggestions.categories)
  const supportedLocales = ['fr', 'da', 'sv']
  const availableLocales = $derived(
    [...new Set(categories.map((category) => category.locale))].sort()
  )
  const filterCategoryOptions = $derived([
    { value: '', label: m['admin.suggestions.allCategories']() },
    ...categories
      .filter((category) => !locale || category.locale === locale)
      .map((category) => ({ value: category.id, label: category.title }))
  ])
  const promptCategoryOptions = $derived([
    { value: '', label: m['admin.suggestions.category']() },
    ...categories
      .filter((category) => category.locale === promptLocale)
      .map((category) => ({ value: category.id, label: category.title }))
  ])
  const localeOptions = $derived([
    { value: '', label: m['admin.suggestions.allLocales']() },
    ...availableLocales.map((value) => ({ value, label: value.toUpperCase() }))
  ])
  const promptLocaleOptions = $derived(
    availableLocales.map((value) => ({ value, label: value.toUpperCase() }))
  )
  const categoryLocaleOptions = supportedLocales.map((value) => ({
    value,
    label: value.toUpperCase()
  }))
  const categoryIconOptions = [
    { value: 'i-ri-lightbulb-line', label: m['admin.suggestions.iconLightbulb']() },
    { value: 'i-ri-draft-line', label: m['admin.suggestions.iconDocument']() },
    { value: 'i-ri-question-answer-line', label: m['admin.suggestions.iconDiscussion']() },
    { value: 'i-ri-book-open-line', label: m['admin.suggestions.iconBook']() },
    { value: 'i-ri-flask-line', label: m['admin.suggestions.iconScience']() },
    { value: 'i-ri-translate-2', label: m['admin.suggestions.iconTranslation']() },
    { value: 'i-ri-restaurant-line', label: m['admin.suggestions.iconFood']() },
    { value: 'i-ri-magic-line', label: m['admin.suggestions.iconCreative']() },
    { value: 'i-ri-folder-line', label: m['admin.suggestions.iconFolder']() },
    { value: 'i-ri-file-text-line', label: m['admin.suggestions.iconWriting']() },
    { value: 'i-ri-graduation-cap-line', label: m['admin.suggestions.iconLearning']() },
    { value: 'i-ri-global-line', label: m['admin.suggestions.iconWorld']() },
    { value: 'i-ri-heart-line', label: m['admin.suggestions.iconWellbeing']() },
    { value: 'i-ri-leaf-line', label: m['admin.suggestions.iconEnvironment']() },
    { value: 'i-ri-map-pin-line', label: m['admin.suggestions.iconTravel']() },
    { value: 'i-ri-music-2-line', label: m['admin.suggestions.iconMusic']() },
    { value: 'i-ri-palette-line', label: m['admin.suggestions.iconArt']() },
    { value: 'i-ri-presentation-line', label: m['admin.suggestions.iconPresentation']() },
    { value: 'i-ri-search-line', label: m['admin.suggestions.iconResearch']() },
    { value: 'i-ri-settings-4-line', label: m['admin.suggestions.iconSettings']() },
    { value: 'i-ri-shopping-bag-line', label: m['admin.suggestions.iconShopping']() },
    { value: 'i-ri-user-line', label: m['admin.suggestions.iconProfile']() },
    { value: 'i-ri-computer-line', label: m['admin.suggestions.iconTechnology']() }
  ]
  const statusOptions: { value: '' | SuggestionStatus; label: string }[] = [
    { value: '', label: m['admin.suggestions.allStatuses']() },
    { value: 'available', label: m['admin.suggestions.available']() },
    { value: 'archived', label: m['admin.suggestions.archived']() }
  ]

  const rows = $derived(
    data.suggestions.items.map((suggestion) => ({
      ...suggestion,
      id: suggestion.id,
      search: toSearchString([suggestion.text, suggestion.category_title, suggestion.locale]),
      actions: undefined
    }))
  )
  type SuggestionColumn = 'text' | 'category_title' | 'locale' | 'status' | 'actions'
  // Not orderable: the server paginates and returns available suggestions
  // first, so sorting here would only reorder the current page.
  const cols = [
    { id: 'text', label: m['admin.suggestions.prompt']() },
    { id: 'category_title', label: m['admin.suggestions.category']() },
    { id: 'locale', label: m['admin.suggestions.locale']() },
    { id: 'status', label: m['admin.suggestions.status']() },
    { id: 'actions', label: m['admin.suggestions.actions']() }
  ] satisfies TableCol<SuggestionColumn>[]

  $effect(() => {
    search = data.filters.search
    status = data.filters.status
    locale = data.filters.locale
    categoryId = data.filters.category_id
    currentPage = data.suggestions.page - 1
  })

  $effect(() => {
    if (search === data.filters.search) return

    const timeout = setTimeout(() => updateQuery({ search, page: '1' }), 300)
    return () => clearTimeout(timeout)
  })

  $effect(() => {
    if (currentPage === data.suggestions.page - 1) return
    updateQuery({ page: String(currentPage + 1) })
  })

  function updateQuery(updates: Record<string, string>) {
    const params = new SvelteURLSearchParams(page.url.searchParams)

    for (const [key, value] of Object.entries(updates)) {
      if (value) params.set(key, value)
      else params.delete(key)
    }

    goto(resolve(`${baseRoute}?${params.toString()}`))
  }

  function updateFilters() {
    updateQuery({ status, locale, category_id: categoryId, page: '1' })
  }

  function updateLocaleFilter() {
    if (
      categoryId &&
      !categories.some((category) => category.id === categoryId && category.locale === locale)
    ) {
      categoryId = ''
    }
    updateFilters()
  }

  function openAddModal() {
    prompt = ''
    formError = undefined
    promptLocale = availableLocales.includes('fr') ? 'fr' : (availableLocales[0] ?? 'fr')
    promptCategoryId = ''
    discloseModal('fr-modal-add-suggestion')
  }

  function openStatusModal(suggestion: PromptSuggestion) {
    suggestionToToggle = suggestion
    discloseModal('fr-modal-suggestion-status')
  }

  function openAddCategoryModal() {
    categoryLocale = 'fr'
    categoryTitle = ''
    categoryDescription = ''
    categoryIcon = 'i-ri-lightbulb-line'
    categoryTooltip = ''
    categoryFormError = undefined
    discloseModal('fr-modal-add-suggestion-category')
  }

  function discloseModal(id: string) {
    const element = document.getElementById(id)
    if (element) {
      // @ts-expect-error - DSFR is globally available
      window.dsfr(element).modal.disclose()
    }
  }

  function closeModal(id: string) {
    const element = document.getElementById(id)
    if (element) {
      // @ts-expect-error - DSFR is globally available
      window.dsfr(element).modal.conceal()
    }
  }

  async function createSuggestion(event: SubmitEvent) {
    event.preventDefault()
    const text = prompt.trim()
    if (!text || !promptCategoryId) {
      formError = m['admin.suggestions.validation']()
      return
    }

    formLoading = true
    formError = undefined
    try {
      await api.request('/admin/suggestions', {
        method: 'POST',
        body: JSON.stringify({ text, category_id: promptCategoryId })
      })
      closeModal('fr-modal-add-suggestion')
      useToast(m['admin.suggestions.createSuccess'](), 4000)
      await refetch()
    } catch (error) {
      const { status, message } = error as ApiError
      formError = status === 409 ? m['admin.suggestions.duplicateError']() : message
    } finally {
      formLoading = false
    }
  }

  async function createCategory(event: SubmitEvent) {
    event.preventDefault()
    const title = categoryTitle.trim()
    const description = categoryDescription.trim()
    const tooltip = categoryTooltip.trim()
    if (!title || !description || !categoryIcon) {
      categoryFormError = m['admin.suggestions.categoryValidation']()
      return
    }

    categoryFormLoading = true
    categoryFormError = undefined
    try {
      await api.request('/admin/suggestions/categories', {
        method: 'POST',
        body: JSON.stringify({
          locale: categoryLocale,
          title,
          description,
          icon: categoryIcon,
          tooltip: tooltip || null
        })
      })
      closeModal('fr-modal-add-suggestion-category')
      useToast(m['admin.suggestions.categoryCreateSuccess'](), 4000)
      await refetch()
    } catch (error) {
      const { status, message } = error as ApiError
      if (status === 409) {
        categoryFormError = m['admin.suggestions.categoryDuplicateError']()
      } else if (status === 422) {
        categoryFormError = m['admin.suggestions.categoryTitleUnusableError']()
      } else {
        categoryFormError = message
      }
    } finally {
      categoryFormLoading = false
    }
  }

  async function confirmStatusChange() {
    if (!suggestionToToggle) return

    actionLoading = true
    const archive = suggestionToToggle.status !== 'archived'
    try {
      await api.request(`/admin/suggestions/${suggestionToToggle.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ archived: archive })
      })
      closeModal('fr-modal-suggestion-status')
      useToast(
        archive ? m['admin.suggestions.archiveSuccess']() : m['admin.suggestions.restoreSuccess'](),
        4000
      )
      await refetch()
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      actionLoading = false
    }
  }

  function statusLabel(value: SuggestionStatus) {
    return value === 'archived'
      ? m['admin.suggestions.archived']()
      : m['admin.suggestions.available']()
  }
</script>

<PageLayout
  seoTitle={m['admin.suggestions.title']()}
  title={m['admin.suggestions.title']()}
  subtitle={m['admin.suggestions.subtitle']()}
>
  <Table
    bind:search
    caption={m['admin.suggestions.tableCaption']()}
    hideCaption
    {cols}
    {rows}
    searchLabel={m['words.search']()}
  >
    {#snippet headerLeft()}
      <div class="gap-3 md:flex-row flex flex-col flex-wrap">
        <Select
          id="suggestions-status-filter"
          label={m['admin.suggestions.status']()}
          options={statusOptions}
          bind:selected={status}
          onchange={updateFilters}
        />
        <Select
          id="suggestions-locale-filter"
          label={m['admin.suggestions.locale']()}
          options={localeOptions}
          bind:selected={locale}
          onchange={updateLocaleFilter}
        />
        <Select
          id="suggestions-category-filter"
          label={m['admin.suggestions.category']()}
          options={filterCategoryOptions}
          bind:selected={categoryId}
          onchange={updateFilters}
        />
      </div>
    {/snippet}

    {#snippet headerRight()}
      <div class="gap-2 flex flex-wrap justify-end">
        <CategoryManager {categories} onDeleted={refetch} />
        <Button
          variant="secondary"
          class="gap-2"
          aria-controls="fr-modal-add-suggestion-category"
          data-fr-opened="false"
          onclick={openAddCategoryModal}
        >
          <Icon icon="i-ri-folder-add-line" aria-hidden="true" />
          <span>{m['admin.suggestions.addCategory']()}</span>
        </Button>
        <Button
          text={m['admin.suggestions.add']()}
          icon="add-line"
          aria-controls="fr-modal-add-suggestion"
          data-fr-opened="false"
          onclick={openAddModal}
        />
      </div>
    {/snippet}

    {#snippet cell(row, col)}
      {#if col.id === 'text'}
        <span class="fr-text--sm whitespace-pre-wrap">{row.text}</span>
      {:else if col.id === 'status'}
        <Badge
          size="sm"
          text={statusLabel(row.status)}
          variant={row.status === 'archived' ? 'orange' : 'green'}
        />
      {:else if col.id === 'locale'}
        <span class="fr-text--sm uppercase">{row.locale}</span>
      {:else if col.id === 'actions'}
        <div class="flex justify-end">
          <Button
            iconOnly
            variant="tertiary-no-outline"
            size="sm"
            title={row.status === 'archived'
              ? m['admin.suggestions.restore']()
              : m['admin.suggestions.archive']()}
            aria-label={`${row.status === 'archived' ? m['admin.suggestions.restore']() : m['admin.suggestions.archive']()}: ${row.text}`}
            onclick={() => openStatusModal(row)}
          >
            <Icon
              icon={row.status === 'archived' ? 'i-ri-inbox-unarchive-line' : 'i-ri-archive-line'}
            />
          </Button>
        </div>
      {:else if col.id === 'category_title'}
        <span class="fr-text--sm">{row.category_title}</span>
      {:else}
        <span class="fr-text--sm">{row.text}</span>
      {/if}
    {/snippet}
  </Table>

  {#if data.suggestions.total === 0}
    <p class="fr-text--sm mt-4! text-[--text-mention-grey]">{m['admin.suggestions.empty']()}</p>
  {/if}

  <div class="mt-4 flex justify-center">
    <Pagination
      bind:page={currentPage}
      itemCount={data.suggestions.total}
      maxItemPerPage={data.suggestions.page_size}
    />
  </div>
</PageLayout>

<Modal
  id="fr-modal-add-suggestion-category"
  titleId="fr-modal-title-add-suggestion-category"
  headerClass="md:absolute! md:top-4 md:right-8 md:z-10 md:p-0!"
  contentClass="md:pt-4! mb-6!"
>
  <h2 id="fr-modal-title-add-suggestion-category" class="fr-modal__title">
    {m['admin.suggestions.addCategory']()}
  </h2>
  <form onsubmit={createCategory}>
    <Select
      id="suggestion-category-locale"
      label={m['admin.suggestions.locale']()}
      options={categoryLocaleOptions}
      bind:selected={categoryLocale}
      required
    />
    <div class="fr-input-group">
      <label class="fr-label" for="suggestion-category-title">
        {m['admin.suggestions.categoryTitle']()}
        <span id="suggestion-category-title-limit" class="fr-hint-text">
          {m['admin.suggestions.charactersMaximum']({ count: 100 })}
        </span>
      </label>
      <input
        id="suggestion-category-title"
        class="fr-input"
        bind:value={categoryTitle}
        required
        maxlength="100"
        aria-describedby="suggestion-category-title-limit"
      />
    </div>

    <div class="fr-input-group">
      <label class="fr-label" for="suggestion-category-description">
        {m['admin.suggestions.categoryDescription']()}
        <span id="suggestion-category-description-hint" class="fr-hint-text">
          {m['admin.suggestions.categoryDescriptionHint']()}
        </span>
        <span id="suggestion-category-description-limit" class="fr-hint-text">
          {m['admin.suggestions.charactersMaximum']({ count: 300 })}
        </span>
      </label>
      <textarea
        id="suggestion-category-description"
        class="fr-input"
        bind:value={categoryDescription}
        required
        maxlength="300"
        aria-describedby="suggestion-category-description-hint suggestion-category-description-limit"
      ></textarea>
    </div>

    <div class="fr-input-group">
      <label class="fr-label" for="suggestion-category-tooltip">
        {m['admin.suggestions.categoryTooltip']()}
        <span id="suggestion-category-tooltip-hint" class="fr-hint-text">
          {m['admin.suggestions.categoryTooltipHint']()}
        </span>
        <span id="suggestion-category-tooltip-limit" class="fr-hint-text">
          {m['admin.suggestions.charactersMaximum']({ count: 300 })}
        </span>
      </label>
      <textarea
        id="suggestion-category-tooltip"
        class="fr-input"
        bind:value={categoryTooltip}
        maxlength="300"
        aria-describedby="suggestion-category-tooltip-hint suggestion-category-tooltip-limit suggestion-category-messages"
      ></textarea>
    </div>
    <CategoryIconPicker
      id="suggestion-category-icon"
      label={m['admin.suggestions.categoryIcon']()}
      options={categoryIconOptions}
      bind:value={categoryIcon}
    />
    {#if categoryFormError}
      <div class="fr-messages-group" id="suggestion-category-messages" aria-live="polite">
        <p class="fr-message fr-message--error">{categoryFormError}</p>
      </div>
    {/if}
    <div class="mt-6 gap-4 sm:flex-row sm:justify-end flex flex-col-reverse">
      <Button
        type="button"
        text={m['admin.suggestions.cancel']()}
        variant="secondary"
        onclick={() => closeModal('fr-modal-add-suggestion-category')}
      />
      <Button
        type="submit"
        text={m['admin.suggestions.addCategory']()}
        disabled={categoryFormLoading}
      />
    </div>
  </form>
</Modal>

<Modal
  id="fr-modal-add-suggestion"
  titleId="fr-modal-title-add-suggestion"
  headerClass="md:absolute! md:top-4 md:right-8 md:z-10 md:p-0!"
  contentClass="md:pt-4! mb-6!"
>
  <h2 id="fr-modal-title-add-suggestion" class="fr-modal__title">
    {m['admin.suggestions.add']()}
  </h2>
  <form onsubmit={createSuggestion}>
    <Select
      id="suggestion-locale"
      label={m['admin.suggestions.locale']()}
      options={promptLocaleOptions}
      bind:selected={promptLocale}
      onchange={() => (promptCategoryId = '')}
    />
    <Select
      id="suggestion-category"
      label={m['admin.suggestions.category']()}
      options={promptCategoryOptions}
      bind:selected={promptCategoryId}
      required
    />
    <div class={['fr-input-group', { 'fr-input-group--error': !!formError }]}>
      <label class="fr-label" for="suggestion-text">
        {m['admin.suggestions.prompt']()}
        <span class="fr-hint-text">{m['admin.suggestions.promptHint']()}</span>
      </label>
      <textarea
        id="suggestion-text"
        class="fr-input"
        bind:value={prompt}
        required
        maxlength="4000"
        aria-describedby="suggestion-text-messages"
      ></textarea>
      {#if formError}
        <div class="fr-messages-group" id="suggestion-text-messages" aria-live="polite">
          <p class="fr-message fr-message--error">{formError}</p>
        </div>
      {/if}
    </div>
    <div class="mt-6 gap-4 sm:flex-row sm:justify-end flex flex-col-reverse">
      <Button
        type="button"
        text={m['admin.suggestions.cancel']()}
        variant="secondary"
        onclick={() => closeModal('fr-modal-add-suggestion')}
      />
      <Button type="submit" text={m['admin.suggestions.add']()} disabled={formLoading} />
    </div>
  </form>
</Modal>

<Modal
  id="fr-modal-suggestion-status"
  titleId="fr-modal-title-suggestion-status"
  headerClass="md:absolute! md:top-4 md:right-8 md:z-10 md:p-0!"
  contentClass="md:pt-4! mb-6!"
>
  <h2 id="fr-modal-title-suggestion-status" class="fr-modal__title">
    {suggestionToToggle?.status === 'archived'
      ? m['admin.suggestions.restore']()
      : m['admin.suggestions.archive']()}
  </h2>
  <p>
    {suggestionToToggle?.status === 'archived'
      ? m['admin.suggestions.restoreConfirm']()
      : m['admin.suggestions.archiveConfirm']()}
  </p>
  <div class="mt-6 gap-4 sm:flex-row sm:justify-end flex flex-col-reverse">
    <Button
      text={m['admin.suggestions.cancel']()}
      variant="secondary"
      onclick={() => closeModal('fr-modal-suggestion-status')}
    />
    <Button
      text={m['admin.suggestions.confirm']()}
      disabled={actionLoading}
      onclick={confirmStatusChange}
    />
  </div>
</Modal>
