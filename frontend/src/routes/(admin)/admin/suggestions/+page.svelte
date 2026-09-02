<script lang="ts">
  import { goto, invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Badge, Button, Icon, Modal, Pagination, Search, Select } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api, type ApiError } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { SvelteSet, SvelteURLSearchParams } from 'svelte/reactivity'
  import type { PageProps } from './$types'
  import CategoryIconPicker from './CategoryIconPicker.svelte'
  import type { PromptSuggestion, SuggestionCategory, SuggestionStatus } from './types'

  let { data }: PageProps = $props()

  const refetch = () => invalidate('admin:suggestions')
  const baseRoute = '/admin/suggestions'
  const params = new SvelteURLSearchParams(page.url.searchParams)

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
  // svelte-ignore state_referenced_locally
  let pageSize = $state(data.suggestions.page_size)
  let suggestionToToggle = $state<PromptSuggestion | null>(null)
  let categoryToToggle = $state<SuggestionCategory | null>(null)
  const collapsedCategoryIds = new SvelteSet<string>()
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
  const pageSizeOptions = [10, 25, 50].map((value) => ({
    value,
    label: m['components.table.pageCount']({ count: value })
  }))

  function isCategoryArchived(category: SuggestionCategory) {
    return category.archived
  }

  const groupedSuggestions = $derived(
    categories
      .map((category) => ({
        category,
        suggestions: data.suggestions.items.filter(
          (suggestion) => suggestion.category_id === category.id
        )
      }))
      .filter((group) => group.suggestions.length > 0)
      .sort(
        (left, right) =>
          Number(isCategoryArchived(left.category)) - Number(isCategoryArchived(right.category))
      )
  )

  function toggleCategory(categoryId: string) {
    if (collapsedCategoryIds.has(categoryId)) collapsedCategoryIds.delete(categoryId)
    else collapsedCategoryIds.add(categoryId)
  }

  $effect(() => {
    search = data.filters.search
    status = data.filters.status
    locale = data.filters.locale
    categoryId = data.filters.category_id
    currentPage = data.suggestions.page - 1
    pageSize = data.suggestions.page_size
  })

  $effect(() => {
    if (search === data.filters.search) return

    const timeout = setTimeout(() => updateQuery({ search, page: 1 }), 300)
    return () => clearTimeout(timeout)
  })

  $effect(() => {
    if (currentPage === data.suggestions.page - 1) return
    updateQuery({ page: currentPage + 1 })
  })

  function updateQuery(updates: Record<string, any>) {
    for (const [key, value] of Object.entries(updates)) {
      if (value) params.set(key, value.toString())
      else params.delete(key)
    }

    goto(resolve(`${baseRoute}?${params.toString()}`))
  }

  function updateFilters() {
    updateQuery({ status, language: locale, category_id: categoryId, page: 1 })
  }

  function updatePageSize() {
    updateQuery({ page_size: pageSize, page: 1 })
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

  function openCategoryStatusModal(category: SuggestionCategory) {
    categoryToToggle = category
    discloseModal('fr-modal-suggestion-category-status')
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

  async function confirmCategoryStatusChange() {
    if (!categoryToToggle) return

    actionLoading = true
    const archive = !categoryToToggle.archived
    try {
      await api.request(`/admin/suggestions/categories/${categoryToToggle.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ archived: archive })
      })
      closeModal('fr-modal-suggestion-category-status')
      useToast(
        archive
          ? m['admin.suggestions.categoryArchiveSuccess']()
          : m['admin.suggestions.categoryRestoreSuccess'](),
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
  <div class="mb-6 gap-4 flex flex-col">
    <div
      class="gap-3 md:grid-cols-2 xl:grid-cols-[minmax(18rem,2fr)_repeat(3,minmax(9rem,1fr))] grid w-full"
    >
      <div>
        <span class="fr-label mb-2! block" aria-hidden="true">
          {m['admin.suggestions.searchFilter']()}
        </span>
        <Search
          id="suggestions-search"
          label={m['admin.suggestions.search']()}
          bind:value={search}
        />
      </div>
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
    <div class="gap-2 flex flex-wrap justify-end">
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
      <Button text={m['admin.suggestions.add']()} icon="add-line" onclick={openAddModal} />
    </div>
  </div>

  <p class="fr-text--sm mb-4! text-[--text-mention-grey]" aria-live="polite">
    {m['admin.suggestions.resultCount']({ count: data.suggestions.total })}
  </p>

  <div class="gap-5 flex flex-col">
    {#each groupedSuggestions as group (group.category.id)}
      {@const isArchived = isCategoryArchived(group.category)}
      {@const isCollapsed = collapsedCategoryIds.has(group.category.id)}
      <section
        class="overflow-hidden border border-[--border-default-grey] bg-[--background-default-grey]"
        aria-labelledby={`suggestion-category-${group.category.id}`}
      >
        <header
          class="gap-4 p-4 md:p-5 md:flex-row md:items-start flex flex-col justify-between bg-[--background-alt-grey]"
        >
          <div class="min-w-0">
            <div class="gap-2 flex flex-wrap items-center">
              <Icon icon={group.category.icon} class="text-primary text-xl" aria-hidden="true" />
              <h2 id={`suggestion-category-${group.category.id}`} class="fr-h5 mb-0!">
                {group.category.title}
              </h2>
              <button
                type="button"
                class="p-1 flex items-center justify-center"
                aria-expanded={!isCollapsed}
                aria-controls={`suggestions-list-${group.category.id}`}
                aria-label={`${isCollapsed ? m['admin.suggestions.expandCategory']() : m['admin.suggestions.collapseCategory']()}: ${group.category.title}`}
                onclick={() => toggleCategory(group.category.id)}
              >
                <Icon
                  icon={isCollapsed ? 'i-ri-arrow-down-s-line' : 'i-ri-arrow-up-s-line'}
                  aria-hidden="true"
                />
              </button>
              <Badge size="sm" text={group.category.locale.toUpperCase()} />
              {#if isArchived}
                <Badge size="sm" text={m['admin.suggestions.archived']()} variant="orange" />
              {/if}
            </div>
            <p class="fr-text--sm mb-0! mt-2! text-[--text-mention-grey]">
              {group.category.description}
            </p>
            <p class="fr-text--xs mb-0! mt-2!">
              {m['admin.suggestions.categoryCountSummary']({
                available: group.category.available_suggestion_count,
                total: group.category.suggestion_count
              })}
            </p>
          </div>
          {#if group.category.suggestion_count > 0}
            <Button
              variant="tertiary"
              size="sm"
              class="gap-2 shrink-0"
              aria-label={`${isArchived ? m['admin.suggestions.restoreCategory']() : m['admin.suggestions.archiveCategory']()}: ${group.category.title}`}
              onclick={() => openCategoryStatusModal(group.category)}
            >
              <Icon icon={isArchived ? 'i-ri-inbox-unarchive-line' : 'i-ri-archive-line'} />
              <span
                >{isArchived
                  ? m['admin.suggestions.restoreCategory']()
                  : m['admin.suggestions.archiveCategory']()}</span
              >
            </Button>
          {/if}
        </header>
        {#if !isCollapsed}
          <ul id={`suggestions-list-${group.category.id}`} class="m-0! p-0! list-none!">
            {#each group.suggestions as suggestion (suggestion.id)}
              <li
                class="gap-4 px-4 py-3 md:px-5 md:flex-row md:items-center flex flex-col justify-between border-t border-[--border-default-grey] first:border-t-0"
              >
                <div class="min-w-0 gap-3 flex items-start">
                  <Badge
                    size="sm"
                    text={statusLabel(suggestion.status)}
                    variant={suggestion.status === 'archived' ? 'orange' : 'green'}
                  />
                  <p class="fr-text--sm mb-0! whitespace-pre-wrap">{suggestion.text}</p>
                </div>
                <Button
                  variant="tertiary-no-outline"
                  size="sm"
                  class="gap-2 md:self-auto shrink-0 self-end"
                  aria-label={`${suggestion.status === 'archived' ? m['admin.suggestions.restore']() : m['admin.suggestions.archive']()}: ${suggestion.text}`}
                  onclick={() => openStatusModal(suggestion)}
                >
                  <Icon
                    icon={suggestion.status === 'archived'
                      ? 'i-ri-inbox-unarchive-line'
                      : 'i-ri-archive-line'}
                  />
                  <span
                    >{suggestion.status === 'archived'
                      ? m['admin.suggestions.restore']()
                      : m['admin.suggestions.archive']()}</span
                  >
                </Button>
              </li>
            {/each}
          </ul>
        {/if}
      </section>
    {/each}
  </div>

  {#if data.suggestions.total > 0}
    <div
      class="mt-6 gap-4 md:flex-row md:items-center pt-4 flex flex-col justify-between border-t-2 border-[--border-default-grey]"
    >
      <Select
        id="suggestions-page-size"
        label={m['components.table.linePerPage']()}
        options={pageSizeOptions}
        bind:selected={pageSize}
        onchange={updatePageSize}
        hideLabel
      />
      <Pagination
        itemCount={data.suggestions.total}
        bind:page={currentPage}
        maxItemPerPage={data.suggestions.page_size}
      />
    </div>
  {/if}

  {#if data.suggestions.total === 0}
    <p class="fr-text--sm mt-4! text-[--text-mention-grey]">{m['admin.suggestions.empty']()}</p>
  {/if}
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

<Modal
  id="fr-modal-suggestion-category-status"
  titleId="fr-modal-title-suggestion-category-status"
  headerClass="md:absolute! md:top-4 md:right-8 md:z-10 md:p-0!"
  contentClass="md:pt-4! mb-6!"
>
  {@const categoryIsArchived = categoryToToggle?.archived ?? false}
  <h2 id="fr-modal-title-suggestion-category-status" class="fr-modal__title">
    {categoryIsArchived
      ? m['admin.suggestions.restoreCategory']()
      : m['admin.suggestions.archiveCategory']()}
  </h2>
  <p>
    {categoryIsArchived
      ? m['admin.suggestions.categoryRestoreConfirm']({ title: categoryToToggle?.title ?? '' })
      : m['admin.suggestions.categoryArchiveConfirm']({
          title: categoryToToggle?.title ?? '',
          count: categoryToToggle?.suggestion_count ?? 0
        })}
  </p>
  <div class="mt-6 gap-4 sm:flex-row sm:justify-end flex flex-col-reverse">
    <Button
      text={m['admin.suggestions.cancel']()}
      variant="secondary"
      onclick={() => closeModal('fr-modal-suggestion-category-status')}
    />
    <Button
      text={categoryIsArchived
        ? m['admin.suggestions.restoreCategory']()
        : m['admin.suggestions.archiveCategory']()}
      disabled={actionLoading}
      onclick={confirmCategoryStatusChange}
    />
  </div>
</Modal>
