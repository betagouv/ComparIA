<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { getAuthContext } from '$lib/auth.svelte'
  import {
    Accordion,
    AccordionGroup,
    Badge,
    Button,
    Icon,
    Input,
    Modal,
    Select,
    Table,
    Toggle
  } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api, type ApiError } from '$lib/fastapi-client'
  import type {
    AdminSurveyCombination,
    AdminSurveyOption,
    AdminSurveyQuestion,
    SurveyOptionWrite,
    SurveyQuestionCreate,
    SurveyQuestionUpdate
  } from '$lib/generated/admin'
  import { getLocales } from '$lib/global.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { TableCol } from '$lib/utils/data'
  import type { PageData } from './$types'

  let { data }: { data: PageData } = $props()

  type SurveyTrigger = AdminSurveyQuestion['trigger']
  type SurveyInputType = AdminSurveyQuestion['input_type']

  const auth = getAuthContext()
  const refetch = () => invalidate('admin:survey')

  // The default locale mints the published key, so its field comes first and
  // carries the hint, and its label is the one the lists show. Only the
  // locales the instance actually serves, same set as the language switcher.
  const defaultLocale = $derived(data.defaultLocale)
  const orderedLocales = $derived(
    getLocales(auth.config.enabled_locales).sort(
      (left, right) => Number(right.code === defaultLocale) - Number(left.code === defaultLocale)
    )
  )

  // A reorder shows up here first and the request only confirms it, so moving
  // three questions is three clicks rather than three round trips. Cleared as
  // soon as the server answers, which makes its order the one on screen again.
  let optimistic = $state<AdminSurveyQuestion[]>()
  let moveSeq = 0
  let announcement = $state('')
  const questions = $derived(optimistic ?? data.survey.questions)

  const triggers: SurveyTrigger[] = ['signup', 'after_vote']
  const byTrigger = $derived({
    signup: questions.filter((question) => question.trigger === 'signup'),
    after_vote: questions.filter((question) => question.trigger === 'after_vote')
  })

  const cols = [
    { id: 'order', label: m['survey.admin.colOrder']() },
    { id: 'label', label: m['survey.admin.colLabel']() },
    { id: 'type', label: m['survey.admin.colType']() },
    { id: 'options', label: m['survey.admin.colOptions']() },
    { id: 'revision', label: m['survey.admin.colRevision']() },
    { id: 'published', label: m['survey.admin.colPublished']() },
    { id: 'respondents', label: m['survey.admin.colRespondents']() },
    { id: 'status', label: m['survey.admin.colStatus']() },
    { id: 'actions', label: m['survey.admin.colActions']() }
  ] satisfies TableCol[]

  let busy = $state(false)
  let formError = $state<string>()
  let editing = $state<AdminSurveyQuestion>()
  let questionToDelete = $state<AdminSurveyQuestion>()
  let deleteConflict = $state(false)

  let formTrigger = $state<SurveyTrigger>('signup')
  let formInputType = $state<SurveyInputType>('select')
  let formLabels = $state<Record<string, string>>({})
  let formPublished = $state(false)

  // Absent `key` means "new option"; present means "keep this option, and
  // every answer pointing at it, attached to the row". Editing only ever
  // loads the live options: one left out of the payload on submit is what
  // tells the backend to archive it instead of deleting it.
  type FormOption = { key?: string; labels: Record<string, string> }
  let formOptions = $state<FormOption[]>([])

  // Mirrors the backend's key-derivation rule, see `_key` in
  // backend/survey/services.py.
  function slug(value: string) {
    return value
      .normalize('NFKD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 100)
  }

  const keyPreview = $derived(
    slug(formLabels[defaultLocale] || Object.values(formLabels).find(Boolean) || '')
  )

  function discloseModal(id: string) {
    const element = document.getElementById(id)
    // @ts-expect-error - DSFR is globally available
    if (element) window.dsfr(element).modal.disclose()
  }

  function closeModal(id: string) {
    const element = document.getElementById(id)
    // @ts-expect-error - DSFR is globally available
    if (element) window.dsfr(element).modal.conceal()
  }

  function openAdd(trigger: SurveyTrigger) {
    editing = undefined
    formTrigger = trigger
    formInputType = 'select'
    formLabels = {}
    formPublished = false
    formOptions = [{ labels: {} }, { labels: {} }]
    formError = undefined
    discloseModal('fr-modal-survey-question')
  }

  function openEdit(question: AdminSurveyQuestion) {
    editing = question
    formTrigger = question.trigger
    formInputType = question.input_type
    formLabels = { ...question.labels }
    formPublished = question.published
    formOptions = question.options
      .filter((option) => !option.archived)
      .map((option) => ({ key: option.key, labels: { ...option.labels } }))
    formError = undefined
    discloseModal('fr-modal-survey-question')
  }

  function openDelete(question: AdminSurveyQuestion) {
    questionToDelete = question
    deleteConflict = false
    discloseModal('fr-modal-survey-question-delete')
  }

  function addOption() {
    formOptions = [...formOptions, { labels: {} }]
  }

  function removeOption(index: number) {
    formOptions = formOptions.filter((_, i) => i !== index)
  }

  async function run(action: () => Promise<unknown>, success: string) {
    busy = true
    formError = undefined
    try {
      await action()
      useToast(success, 4000)
      await refetch()
      optimistic = undefined
      return true
    } catch (error) {
      const { status, message } = error as ApiError
      formError =
        status === 409
          ? m['survey.admin.inUseError']()
          : status === 422
            ? m['survey.admin.labelError']()
            : message
      useToast(formError, 6000, 'error')
      return false
    } finally {
      busy = false
    }
  }

  async function submit(event: SubmitEvent) {
    event.preventDefault()

    const labels = Object.fromEntries(
      orderedLocales
        .map(({ code }) => [code, (formLabels[code] ?? '').trim()])
        .filter(([, value]) => value)
    )
    const options: SurveyOptionWrite[] = formOptions
      .map((option) => ({
        key: option.key,
        labels: Object.fromEntries(
          orderedLocales
            .map(({ code }) => [code, (option.labels[code] ?? '').trim()])
            .filter(([, value]) => value)
        )
      }))
      .filter((option) => Object.keys(option.labels).length)

    if (
      !Object.keys(labels).length ||
      options.some((option) => !Object.keys(option.labels).length)
    ) {
      formError = m['survey.admin.labelError']()
      return
    }
    if (options.length < 2) {
      formError = m['survey.admin.optionsError']()
      return
    }

    const target = editing
    const done = await run(
      () =>
        target
          ? api.request(`/admin/survey/${target.id}`, {
              method: 'PUT',
              body: JSON.stringify({
                labels,
                options,
                published: formPublished
              } satisfies SurveyQuestionUpdate)
            })
          : api.request('/admin/survey', {
              method: 'POST',
              body: JSON.stringify({
                trigger: formTrigger,
                input_type: formInputType,
                labels,
                options,
                published: formPublished
              } satisfies SurveyQuestionCreate)
            }),
      target ? m['survey.admin.editSuccess']() : m['survey.admin.createSuccess']()
    )
    if (done) closeModal('fr-modal-survey-question')
  }

  async function reorder(trigger: SurveyTrigger, from: number, to: number) {
    const side = byTrigger[trigger]
    if (from === to || to < 0 || to >= side.length) return

    const reordered = [...side]
    reordered.splice(to, 0, ...reordered.splice(from, 1))
    // A row that moves under the pointer needs saying out loud for anyone
    // driving this from the keyboard.
    announcement = m['survey.admin.moved']({
      label: displayLabel(side[from]),
      position: to + 1,
      total: side.length
    })
    // No 'busy' here: the point is that the next move lands straight away.
    optimistic = [...reordered, ...questions.filter((question) => question.trigger !== trigger)]
    // Moving again before the last request answers would otherwise let the
    // older one drop the newer order on the floor.
    const seq = ++moveSeq

    try {
      await api.request('/admin/survey/order', {
        method: 'PUT',
        body: JSON.stringify({ trigger, ids: reordered.map((question) => question.id) })
      })
    } catch (error) {
      useToast((error as ApiError).message, 6000, 'error')
    }
    await refetch()
    if (seq === moveSeq) optimistic = undefined
  }

  function move(question: AdminSurveyQuestion, direction: 'up' | 'down') {
    const from = byTrigger[question.trigger].findIndex((other) => other.id === question.id)
    return reorder(question.trigger, from, direction === 'up' ? from - 1 : from + 1)
  }

  // Dragging is the shortcut; the up and down buttons stay because a drag is
  // not reachable from a keyboard.
  let dragging = $state<{ trigger: SurveyTrigger; index: number }>()
  let dropTarget = $state<{ trigger: SurveyTrigger; index: number }>()

  function onDragStart(event: DragEvent, trigger: SurveyTrigger, index: number) {
    dragging = { trigger, index }
    event.dataTransfer?.setData('text/plain', String(index))
    if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
  }

  function onDragOver(event: DragEvent, trigger: SurveyTrigger, index: number) {
    // A question only ever moves within its own trigger, so a drag across the
    // two tables is refused rather than silently changing when it is asked.
    if (dragging?.trigger !== trigger) return
    event.preventDefault()
    dropTarget = { trigger, index }
  }

  function onDrop(event: DragEvent, trigger: SurveyTrigger, index: number) {
    event.preventDefault()
    const source = dragging
    dragging = undefined
    dropTarget = undefined
    if (source?.trigger !== trigger) return
    reorder(trigger, source.index, index)
  }

  const setArchived = (question: AdminSurveyQuestion, archived: boolean) =>
    run(
      () =>
        api.request(`/admin/survey/${question.id}`, {
          method: 'PATCH',
          body: JSON.stringify({ archived })
        }),
      archived ? m['survey.admin.archiveSuccess']() : m['survey.admin.restoreSuccess']()
    )

  // The row-level toggle is a plain button rather than a bound DSFR `Toggle`:
  // `questions` is a `$derived` array, so there is nothing safe to two-way
  // bind the switch to, and every flip has to round-trip through the server
  // anyway since `published` only travels on the full `PUT`. The options sent
  // back are the row's current ones, unchanged, so this never touches labels
  // or archives an option by accident.
  function togglePublished(question: AdminSurveyQuestion) {
    const options: SurveyOptionWrite[] = question.options.map((option) => ({
      key: option.key,
      labels: option.labels,
      archived: option.archived
    }))
    return run(
      () =>
        api.request(`/admin/survey/${question.id}`, {
          method: 'PUT',
          body: JSON.stringify({
            labels: question.labels,
            options,
            published: !question.published
          } satisfies SurveyQuestionUpdate)
        }),
      question.published ? m['survey.admin.unpublishSuccess']() : m['survey.admin.publishSuccess']()
    )
  }

  async function confirmDelete() {
    if (!questionToDelete) return
    busy = true
    formError = undefined
    try {
      await api.request(`/admin/survey/${questionToDelete.id}`, { method: 'DELETE' })
      useToast(m['survey.admin.deleteSuccess'](), 4000)
      await refetch()
      optimistic = undefined
      closeModal('fr-modal-survey-question-delete')
      questionToDelete = undefined
    } catch (error) {
      const { status, message } = error as ApiError
      if (status === 409) {
        deleteConflict = true
      } else {
        useToast(message, 6000, 'error')
      }
    } finally {
      busy = false
    }
  }

  async function archiveInstead() {
    if (!questionToDelete) return
    const done = await setArchived(questionToDelete, true)
    if (done) {
      closeModal('fr-modal-survey-question-delete')
      questionToDelete = undefined
      deleteConflict = false
    }
  }

  function displayLabel(question: AdminSurveyQuestion) {
    return question.labels[defaultLocale] ?? Object.values(question.labels)[0] ?? ''
  }

  function optionLabel(option: AdminSurveyOption) {
    return option.labels[defaultLocale] ?? Object.values(option.labels)[0] ?? option.key
  }

  function inputTypeLabel(question: AdminSurveyQuestion) {
    return question.input_type === 'select'
      ? m['survey.admin.inputTypeSelect']()
      : m['survey.admin.inputTypeCheckboxGroup']()
  }

  // Combinations carry question and option *keys*, not labels (see
  // `admin_list` in backend/survey/services.py), so they are resolved against
  // the current question list for display. A checkbox_group answer folds
  // several option keys into one comma-joined string.
  function comboSummary(answers: Record<string, string>) {
    return Object.entries(answers).map(([questionKey, optionKeys]) => {
      const question = questions.find((candidate) => candidate.key === questionKey)
      if (!question) return { question: questionKey, value: optionKeys }
      const optionLabels = optionKeys
        .split(',')
        .map((key) => question.options.find((option) => option.key === key)?.labels[defaultLocale])
        .filter((label): label is string => !!label)
      return {
        question: displayLabel(question),
        value: optionLabels.length ? optionLabels.join(', ') : optionKeys
      }
    })
  }

  type ComboRow = AdminSurveyCombination & { id: string }
  const comboRows = $derived<ComboRow[]>(
    data.survey.combinations.map((combo, index) => ({ ...combo, id: String(index) }))
  )
  const comboCols = [
    { id: 'answers', label: m['survey.admin.colLabel']() },
    { id: 'count', label: m['survey.admin.colRespondents']() }
  ] satisfies TableCol[]
</script>

<PageLayout
  seoTitle={m['survey.admin.title']()}
  title={m['survey.admin.title']()}
  subtitle={m['survey.admin.subtitle']()}
>
  <p class="sr-only" aria-live="polite">{announcement}</p>

  {#each triggers as trigger (trigger)}
    {@const rows = byTrigger[trigger]}
    <section class="mb-10 last:mb-0">
      <Table
        caption={m[`survey.admin.${trigger}`]()}
        hideCaption
        {cols}
        {rows}
        animateRows
        rowAttributes={(row, index) => ({
          draggable: true,
          class:
            dropTarget?.trigger === trigger && dropTarget.index === index
              ? 'bg-very-light-primary'
              : dragging?.trigger === trigger && dragging.index === index
                ? 'opacity-50'
                : undefined,
          ondragstart: (event: DragEvent) => onDragStart(event, trigger, index),
          ondragover: (event: DragEvent) => onDragOver(event, trigger, index),
          ondrop: (event: DragEvent) => onDrop(event, trigger, index),
          ondragend: () => {
            dragging = undefined
            dropTarget = undefined
          }
        })}
      >
        {#snippet headerLeft()}
          <h2 class="fr-h6 mb-0!">{m[`survey.admin.${trigger}`]()}</h2>
        {/snippet}

        {#snippet headerRight()}
          <Button
            text={m['survey.admin.addTitle']()}
            icon="add-line"
            variant="secondary"
            class="md:ms-auto"
            aria-controls="fr-modal-survey-question"
            data-fr-opened="false"
            onclick={() => openAdd(trigger)}
          />
        {/snippet}

        {#snippet cell(row, col)}
          {#if col.id === 'label'}
            <strong class={{ 'text-grey line-through': row.archived }}>
              {displayLabel(row)}
            </strong>
          {:else if col.id === 'type'}
            <span class="fr-text--sm text-grey">{inputTypeLabel(row)}</span>
          {:else if col.id === 'options'}
            <span class="fr-text--sm text-grey">
              {row.options.filter((option) => !option.archived).length}
            </span>
          {:else if col.id === 'revision'}
            <span class="fr-text--sm text-grey">{row.revision}</span>
          {:else if col.id === 'published'}
            <span class="gap-2 flex flex-col items-start">
              <Badge
                size="sm"
                text={row.published
                  ? m['survey.admin.published']()
                  : m['survey.admin.notPublished']()}
                variant={row.published ? 'purple' : ''}
              />
              <Button
                size="sm"
                variant="tertiary-no-outline"
                text={row.published
                  ? m['survey.admin.unpublishAction']()
                  : m['survey.admin.publishAction']()}
                disabled={busy}
                onclick={() => togglePublished(row)}
              />
            </span>
          {:else if col.id === 'respondents'}
            <span class="fr-text--sm text-grey">{row.respondent_count}</span>
          {:else if col.id === 'status'}
            <Badge
              size="sm"
              text={row.archived ? m['survey.admin.archived']() : m['survey.admin.active']()}
              variant={row.archived ? 'orange' : 'green'}
            />
          {:else if col.id === 'order'}
            <span class="gap-1 flex items-center">
              <Icon
                icon="i-ri-draggable"
                class="text-grey cursor-grab"
                aria-hidden="true"
                title={m['survey.admin.dragHint']()}
              />
              <Button
                size="sm"
                variant="tertiary-no-outline"
                icon="arrow-up-line"
                iconOnly
                text={m['survey.admin.moveUp']()}
                title={m['survey.admin.moveUp']()}
                disabled={busy || rows[0]?.id === row.id}
                onclick={() => move(row, 'up')}
              />
              <Button
                size="sm"
                variant="tertiary-no-outline"
                icon="arrow-down-line"
                iconOnly
                text={m['survey.admin.moveDown']()}
                title={m['survey.admin.moveDown']()}
                disabled={busy || rows[rows.length - 1]?.id === row.id}
                onclick={() => move(row, 'down')}
              />
            </span>
          {:else if col.id === 'actions'}
            <span class="gap-1 flex justify-end">
              <Button
                size="sm"
                variant="tertiary-no-outline"
                iconOnly
                title={m['survey.admin.edit']()}
                aria-label={`${m['survey.admin.edit']()} : ${displayLabel(row)}`}
                disabled={busy}
                aria-controls="fr-modal-survey-question"
                data-fr-opened="false"
                onclick={() => openEdit(row)}
              >
                <Icon icon="i-ri-edit-line" />
              </Button>
              <Button
                size="sm"
                variant="tertiary-no-outline"
                iconOnly
                title={row.archived ? m['survey.admin.restore']() : m['survey.admin.archive']()}
                aria-label={`${row.archived ? m['survey.admin.restore']() : m['survey.admin.archive']()} : ${displayLabel(row)}`}
                disabled={busy}
                onclick={() => setArchived(row, !row.archived)}
              >
                <Icon icon={row.archived ? 'i-ri-eye-line' : 'i-ri-eye-off-line'} />
              </Button>
              {#if row.respondent_count === 0}
                <Button
                  size="sm"
                  variant="tertiary-no-outline"
                  iconOnly
                  class="text-[--text-default-error]!"
                  title={m['survey.admin.delete']()}
                  aria-label={`${m['survey.admin.delete']()} : ${displayLabel(row)}`}
                  disabled={busy}
                  aria-controls="fr-modal-survey-question-delete"
                  data-fr-opened="false"
                  onclick={() => openDelete(row)}
                >
                  <Icon icon="i-ri-delete-bin-line" />
                </Button>
              {/if}
            </span>
          {/if}
        {/snippet}
      </Table>

      {#if !rows.length}
        <p class="fr-text--sm mt-2! text-warning">{m['survey.admin.emptyTrigger']()}</p>
      {/if}
    </section>
  {/each}

  <section class="mt-10 pt-8 border-t-1 border-[--border-default-grey]">
    <h2 class="fr-h6">{m['survey.admin.statsTitle']()}</h2>
    <p class="fr-text--sm text-grey">
      {m['survey.admin.statsIntro']({ count: data.survey.total_respondents })}
    </p>

    {#if questions.filter((question) => !question.archived).length}
      <AccordionGroup class="mb-8">
        {#each questions.filter((question) => !question.archived) as question (question.id)}
          <Accordion
            id="survey-stats-{question.id}"
            label={`${displayLabel(question)} — ${question.respondent_count}`}
          >
            <ul class="m-0! space-y-1 p-0! list-none">
              {#each question.options as option (option.key)}
                <li
                  class="gap-2 py-1 flex items-center justify-between border-b-1 border-[--border-default-grey] last:border-0"
                >
                  <span class={{ 'text-grey line-through': option.archived }}>
                    {optionLabel(option)}
                    {#if option.archived}
                      <Badge
                        size="xs"
                        text={m['survey.admin.archived']()}
                        variant="orange"
                        class="ms-1"
                      />
                    {/if}
                  </span>
                  <span class="fr-text--sm text-grey">{option.answer_count}</span>
                </li>
              {/each}
            </ul>
          </Accordion>
        {/each}
      </AccordionGroup>
    {/if}

    <h3 class="fr-h6">{m['survey.admin.combinationsTitle']()}</h3>
    <p class="fr-text--sm text-warning">{m['survey.admin.combinationsIntro']()}</p>

    {#if !comboRows.length}
      <p class="fr-text--sm text-grey">{m['survey.admin.combinationsEmpty']()}</p>
    {:else}
      <Table
        caption={m['survey.admin.combinationsTitle']()}
        hideCaption
        cols={comboCols}
        rows={comboRows}
      >
        {#snippet cell(row, col)}
          {#if col.id === 'answers'}
            <ul class="m-0! space-y-1 p-0! list-none">
              {#each comboSummary(row.answers) as pair (pair.question)}
                <li><strong>{pair.question}</strong> : {pair.value}</li>
              {/each}
            </ul>
          {:else if col.id === 'count'}
            <Badge text={String(row.count)} variant={row.count <= 2 ? 'red' : ''} />
          {/if}
        {/snippet}
      </Table>
    {/if}
  </section>
</PageLayout>

<Modal
  id="fr-modal-survey-question"
  titleId="fr-modal-title-survey-question"
  headerClass="md:absolute! md:top-4 md:right-8 md:z-10 md:p-0!"
  contentClass="md:pt-4! mb-6!"
>
  <h2 id="fr-modal-title-survey-question" class="fr-modal__title">
    {editing ? m['survey.admin.editTitle']() : m['survey.admin.addTitle']()}
  </h2>

  <form onsubmit={submit}>
    {#if !editing}
      <Select
        id="survey-question-trigger"
        bind:selected={formTrigger}
        label={m['survey.admin.triggerLabel']()}
        options={triggers.map((value) => ({ value, label: m[`survey.admin.${value}`]() }))}
      />
      <Select
        id="survey-question-input-type"
        bind:selected={formInputType}
        label={m['survey.admin.inputTypeLabel']()}
        options={[
          { value: 'select', label: m['survey.admin.inputTypeSelect']() },
          { value: 'checkbox_group', label: m['survey.admin.inputTypeCheckboxGroup']() }
        ]}
      />
    {:else}
      <p class="fr-text--sm text-grey">
        {m[`survey.admin.${editing.trigger}`]()} · {inputTypeLabel(editing)}
      </p>
    {/if}

    {#each orderedLocales as locale (locale.code)}
      <Input
        id="survey-question-label-{locale.code}"
        value={formLabels[locale.code] ?? ''}
        oninput={(event) =>
          (formLabels = { ...formLabels, [locale.code]: event.currentTarget.value })}
        label={m['survey.admin.labelFor']({ locale: locale.long })}
        help={locale.code === defaultLocale ? m['survey.admin.labelHelp']() : undefined}
        maxlength={300}
      />
    {/each}

    {#if editing}
      <p class="fr-text--sm text-grey">{m['survey.admin.keyFrozen']({ key: editing.key })}</p>
    {:else if keyPreview}
      <p class="fr-text--sm text-grey">{m['survey.admin.keyPreview']({ key: keyPreview })}</p>
    {/if}

    <fieldset class="fr-fieldset mt-4">
      <legend class="fr-label mb-2!">{m['survey.admin.optionsLegend']()}</legend>

      {#each formOptions as option, index (option.key ?? `new-${index}`)}
        <div class="mb-4 rounded-lg p-3 border-1 border-[--border-default-grey]">
          <div class="mb-2 gap-2 flex items-center justify-between">
            <span class="fr-text--sm font-bold"
              >{m['survey.admin.optionN']({ index: index + 1 })}</span
            >
            <Button
              size="sm"
              variant="tertiary-no-outline"
              icon="delete-bin-line"
              iconOnly
              text={m['survey.admin.removeOption']()}
              title={m['survey.admin.removeOption']()}
              disabled={formOptions.length <= 2}
              onclick={() => removeOption(index)}
            />
          </div>
          {#each orderedLocales as locale (locale.code)}
            <Input
              id="survey-option-{index}-{locale.code}"
              value={option.labels[locale.code] ?? ''}
              oninput={(event) => {
                formOptions[index] = {
                  ...formOptions[index],
                  labels: { ...formOptions[index].labels, [locale.code]: event.currentTarget.value }
                }
              }}
              label={m['survey.admin.optionLabelFor']({ locale: locale.long })}
              maxlength={200}
            />
          {/each}
        </div>
      {/each}

      <Button
        variant="secondary"
        size="sm"
        icon="add-line"
        text={m['survey.admin.addOption']()}
        onclick={addOption}
      />
      <p class="fr-hint-text mt-1!">{m['survey.admin.optionArchivedHint']()}</p>
    </fieldset>

    <div
      class="mt-4 rounded-lg p-3 border-1 border-[--border-default-orange] bg-[--background-alt-orange]"
    >
      <Toggle
        id="survey-question-published"
        bind:value={formPublished}
        label={m['survey.admin.published']()}
      />
      <p class="fr-text--sm mt-1! text-[--text-default-warning]">
        <Icon icon="i-ri-error-warning-line" aria-hidden="true" class="me-1" />
        {m['survey.admin.publishedHelp']()}
      </p>
    </div>

    {#if formError}
      <p class="fr-error-text" aria-live="polite">{formError}</p>
    {/if}

    <div class="mt-6 gap-4 sm:flex-row sm:justify-end flex flex-col-reverse">
      <Button
        type="button"
        variant="secondary"
        text={m['survey.admin.cancel']()}
        onclick={() => closeModal('fr-modal-survey-question')}
      />
      <Button
        type="submit"
        disabled={busy}
        text={editing ? m['survey.admin.save']() : m['survey.admin.addTitle']()}
      />
    </div>
  </form>
</Modal>

<Modal
  id="fr-modal-survey-question-delete"
  titleId="fr-modal-title-survey-question-delete"
  headerClass="md:absolute! md:top-4 md:right-8 md:z-10 md:p-0!"
  contentClass="md:pt-4! mb-6!"
>
  <h2 id="fr-modal-title-survey-question-delete" class="fr-modal__title">
    {m['survey.admin.deleteConfirm']({
      label: questionToDelete ? displayLabel(questionToDelete) : ''
    })}
  </h2>
  {#if deleteConflict}
    <p class="fr-error-text">{m['survey.admin.inUseError']()}</p>
  {:else}
    <p>{m['survey.admin.deleteWarning']()}</p>
  {/if}

  <div class="mt-6 gap-4 sm:flex-row sm:justify-end flex flex-col-reverse">
    <Button
      variant="secondary"
      text={m['survey.admin.cancel']()}
      disabled={busy}
      onclick={() => closeModal('fr-modal-survey-question-delete')}
    />
    {#if deleteConflict}
      <Button text={m['survey.admin.archive']()} disabled={busy} onclick={archiveInstead} />
    {:else}
      <Button text={m['survey.admin.delete']()} disabled={busy} onclick={confirmDelete} />
    {/if}
  </div>
</Modal>
