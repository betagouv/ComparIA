<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Alert, Badge, Button, Checkbox, Icon, Input, Modal, Select, Table, Toggle } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api, type ApiError } from '$lib/fastapi-client'
  import type { AdminPublishDestination, AdminPublishStatus } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { TableCol } from '$lib/utils/data'
  import { untrack } from 'svelte'
  import type { PageData } from './$types'

  let { data }: { data: PageData } = $props()

  const refetch = () => invalidate('admin:publishing')

  type Kind = 'huggingface' | 's3'
  type Dataset = 'normal' | 'raw'
  type Frequency = AdminPublishStatus['frequency']

  const destinations = $derived(data.destinations.destinations)
  const status = $derived(data.status)

  const cols = [
    { id: 'name', label: m['admin.publishing.colName']() },
    { id: 'kind', label: m['admin.publishing.colKind']() },
    { id: 'target', label: m['admin.publishing.colTarget']() },
    { id: 'datasets', label: m['admin.publishing.colDatasets']() },
    { id: 'status', label: m['admin.publishing.colStatus']() },
    { id: 'actions', label: m['admin.publishing.colActions']() }
  ] satisfies TableCol[]

  let busy = $state(false)
  let checking = $state<string>()
  let formError = $state<string>()
  let editing = $state<AdminPublishDestination>()
  let toDelete = $state<AdminPublishDestination>()

  let formName = $state('')
  let formKind = $state<Kind>('huggingface')
  let wantsOpen = $state(true)
  let wantsRaw = $state(false)
  const formDatasets = $derived([
    ...(wantsOpen ? (['normal'] as Dataset[]) : []),
    ...(wantsRaw ? (['raw'] as Dataset[]) : [])
  ])
  let formEnabled = $state(true)
  let formRepoPath = $state('')
  let formToken = $state('')
  let formEndpoint = $state('')
  let formBucket = $state('')
  let formRegion = $state('')
  let formPrefix = $state('')
  let formSecure = $state(true)
  let formAccessKey = $state('')
  let formSecretKey = $state('')

  // Seeded from what the instance has, and left alone afterwards so an
  // administrator's half-made choice survives a refetch of the run status.
  let frequency = $state<Frequency>(untrack(() => data.status.frequency))
  let hour = $state(untrack(() => String(data.status.hour)))
  let timezone = $state(untrack(() => data.status.timezone))

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

  function openAdd() {
    editing = undefined
    formError = undefined
    formName = ''
    formKind = 'huggingface'
    wantsOpen = true
    wantsRaw = false
    formEnabled = true
    formRepoPath = ''
    formEndpoint = ''
    formBucket = ''
    formRegion = ''
    formPrefix = ''
    formSecure = true
    formToken = ''
    formAccessKey = ''
    formSecretKey = ''
    discloseModal('fr-modal-destination')
  }

  function openEdit(destination: AdminPublishDestination) {
    editing = destination
    formError = undefined
    formName = destination.name
    formKind = destination.kind
    wantsOpen = destination.datasets.includes('normal')
    wantsRaw = destination.datasets.includes('raw')
    formEnabled = destination.enabled
    // The secrets never come back from the API, so their fields start empty
    // and an empty field means 'keep the one already stored'.
    formToken = ''
    formAccessKey = ''
    formSecretKey = ''
    const config = destination.config as Record<string, unknown>
    formRepoPath = String(config.repo_path ?? '')
    formEndpoint = String(config.endpoint ?? '')
    formBucket = String(config.bucket ?? '')
    formRegion = String(config.region ?? '')
    formPrefix = String(config.prefix ?? '')
    formSecure = config.secure !== false
    discloseModal('fr-modal-destination')
  }

  async function run(action: () => Promise<unknown>, success: string) {
    busy = true
    formError = undefined
    try {
      await action()
      useToast(success, 4000)
      await refetch()
      return true
    } catch (error) {
      const { message } = error as ApiError
      formError = message
      useToast(message, 6000, 'error')
      return false
    } finally {
      busy = false
    }
  }

  function configPayload() {
    if (formKind === 'huggingface') {
      return {
        kind: 'huggingface',
        repo_path: formRepoPath.trim(),
        ...(formToken.trim() ? { token: formToken.trim() } : {})
      }
    }
    return {
      kind: 's3',
      endpoint: formEndpoint.trim(),
      bucket: formBucket.trim(),
      region: formRegion.trim() || null,
      prefix: formPrefix.trim(),
      secure: formSecure,
      ...(formAccessKey.trim() ? { access_key: formAccessKey.trim() } : {}),
      ...(formSecretKey.trim() ? { secret_key: formSecretKey.trim() } : {})
    }
  }

  async function submit(event: SubmitEvent) {
    event.preventDefault()
    if (!formDatasets.length) {
      formError = m['admin.publishing.datasetsError']()
      return
    }

    const body = JSON.stringify({
      name: formName.trim(),
      config: configPayload(),
      datasets: formDatasets,
      enabled: formEnabled
    })
    const target = editing
    const done = await run(
      () =>
        target
          ? api.request(`/admin/publishing/destinations/${target.id}`, {
              method: 'PUT',
              body
            })
          : api.request('/admin/publishing/destinations', { method: 'POST', body }),
      target
        ? m['admin.publishing.editSuccess']()
        : m['admin.publishing.createSuccess']()
    )
    if (done) closeModal('fr-modal-destination')
  }

  async function check(destination: AdminPublishDestination) {
    checking = destination.id
    try {
      await api.request(`/admin/publishing/destinations/${destination.id}/check`, {
        method: 'POST'
      })
      useToast(m['admin.publishing.checkSuccess'](), 4000)
    } catch (error) {
      useToast(
        m['admin.publishing.checkError']({ message: (error as ApiError).message }),
        8000,
        'error'
      )
    } finally {
      checking = undefined
    }
  }

  const setEnabled = (destination: AdminPublishDestination, enabled: boolean) =>
    run(
      () =>
        api.request(`/admin/publishing/destinations/${destination.id}`, {
          method: 'PUT',
          body: JSON.stringify({
            name: destination.name,
            config: destination.config,
            datasets: destination.datasets,
            enabled
          })
        }),
      m['admin.publishing.editSuccess']()
    )

  async function confirmDelete() {
    if (!toDelete) return
    const done = await run(
      () =>
        api.request(`/admin/publishing/destinations/${toDelete!.id}`, {
          method: 'DELETE'
        }),
      m['admin.publishing.deleteSuccess']()
    )
    if (done) {
      closeModal('fr-modal-destination-delete')
      toDelete = undefined
    }
  }

  const saveSchedule = () =>
    run(
      () =>
        api.request('/admin/settings', {
          method: 'PATCH',
          body: JSON.stringify({
            publish_frequency: frequency,
            publish_hour: Number(hour),
            publish_timezone: timezone
          })
        }),
      m['admin.publishing.scheduleSuccess']()
    )

  function target(destination: AdminPublishDestination) {
    const config = destination.config as Record<string, unknown>
    if (destination.kind === 'huggingface') return String(config.repo_path ?? '')
    const prefix = String(config.prefix ?? '')
    return `${config.bucket}${prefix ? `/${prefix}` : ''} · ${config.endpoint}`
  }

  const datasetLabel = (dataset: string) =>
    dataset === 'raw'
      ? m['admin.publishing.datasetRaw']()
      : m['admin.publishing.datasetNormal']()

  function formatDate(value: string | null) {
    if (!value) return ''
    // The API answers in UTC; an administrator reads their own clock.
    const date = new Date(value.endsWith('Z') ? value : `${value}Z`)
    return date.toLocaleString()
  }

  const hours = Array.from({ length: 24 }, (_, index) => ({
    value: String(index),
    label: `${String(index).padStart(2, '0')}:00`
  }))

  // Whatever the browser is set to, plus whatever the instance already had, so
  // an administrator is not asked to type a time zone from memory.
  const timezones = $derived([
    ...new Set([
      status.timezone,
      Intl.DateTimeFormat().resolvedOptions().timeZone,
      'UTC',
      'Europe/Paris',
      'Europe/Copenhagen'
    ])
  ])

</script>

<PageLayout
  seoTitle={m['admin.publishing.title']()}
  title={m['admin.publishing.title']()}
  subtitle={m['admin.publishing.subtitle']()}
>
  <section class="mb-10">
    <Table
      caption={m['admin.publishing.destinations']()}
      hideCaption
      {cols}
      rows={destinations}
      animateRows
    >
      {#snippet headerLeft()}
        <h2 class="fr-h6 mb-0!">{m['admin.publishing.destinations']()}</h2>
      {/snippet}

      {#snippet headerRight()}
        <Button
          text={m['admin.publishing.addTitle']()}
          icon="add-line"
          variant="secondary"
          class="md:ms-auto"
          aria-controls="fr-modal-destination"
          data-fr-opened="false"
          onclick={openAdd}
        />
      {/snippet}

      {#snippet cell(row, col)}
        {#if col.id === 'name'}
          <strong>{row.name}</strong>
        {:else if col.id === 'kind'}
          {row.kind === 'huggingface'
            ? m['admin.publishing.kindHuggingface']()
            : m['admin.publishing.kindS3']()}
        {:else if col.id === 'target'}
          <code class="text-xs text-grey">{target(row)}</code>
        {:else if col.id === 'datasets'}
          <span class="gap-1 flex flex-wrap">
            {#each row.datasets as dataset (dataset)}
              <Badge
                size="sm"
                text={datasetLabel(dataset)}
                variant={dataset === 'raw' ? 'orange' : 'blue-ecume'}
              />
            {/each}
          </span>
        {:else if col.id === 'status'}
          <Badge
            size="sm"
            text={row.enabled
              ? m['admin.publishing.enabled']()
              : m['admin.publishing.disabled']()}
            variant={row.enabled ? 'green' : ''}
          />
        {:else if col.id === 'actions'}
          <span class="gap-1 flex justify-end">
            <Button
              size="sm"
              variant="tertiary-no-outline"
              text={checking === row.id
                ? m['admin.publishing.checking']()
                : m['admin.publishing.check']()}
              disabled={busy || checking === row.id}
              onclick={() => check(row)}
            />
            <Button
              size="sm"
              variant="tertiary-no-outline"
              iconOnly
              title={m['admin.publishing.edit']()}
              aria-label={`${m['admin.publishing.edit']()} : ${row.name}`}
              disabled={busy}
              aria-controls="fr-modal-destination"
              data-fr-opened="false"
              onclick={() => openEdit(row)}
            >
              <Icon icon="i-ri-edit-line" />
            </Button>
            <Button
              size="sm"
              variant="tertiary-no-outline"
              iconOnly
              title={row.enabled
                ? m['admin.publishing.disable']()
                : m['admin.publishing.enable']()}
              aria-label={`${row.enabled ? m['admin.publishing.disable']() : m['admin.publishing.enable']()} : ${row.name}`}
              disabled={busy}
              onclick={() => setEnabled(row, !row.enabled)}
            >
              <Icon icon={row.enabled ? 'i-ri-pause-line' : 'i-ri-play-line'} />
            </Button>
            <Button
              size="sm"
              variant="tertiary-no-outline"
              iconOnly
              class="text-[--text-default-error]!"
              title={m['admin.publishing.delete']()}
              aria-label={`${m['admin.publishing.delete']()} : ${row.name}`}
              disabled={busy}
              aria-controls="fr-modal-destination-delete"
              data-fr-opened="false"
              onclick={() => {
                toDelete = row
              }}
            >
              <Icon icon="i-ri-delete-bin-line" />
            </Button>
          </span>
        {/if}
      {/snippet}
    </Table>

    {#if !destinations.some((destination) => destination.enabled)}
      <p class="fr-text--sm mt-2! text-warning">
        {m['admin.publishing.noDestinations']()}
      </p>
    {/if}
  </section>

  <section class="mb-10">
    <h2 class="fr-h6">{m['admin.publishing.schedule']()}</h2>

    <div class="gap-4 md:grid-cols-3 grid">
      <Select
        id="publish-frequency"
        bind:selected={frequency}
        label={m['admin.publishing.frequencyLabel']()}
        options={[
          { value: 'off', label: m['admin.publishing.frequencyOff']() },
          { value: 'daily', label: m['admin.publishing.frequencyDaily']() },
          { value: 'weekly', label: m['admin.publishing.frequencyWeekly']() },
          { value: 'monthly', label: m['admin.publishing.frequencyMonthly']() }
        ]}
      />
      <Select
        id="publish-hour"
        bind:selected={hour}
        label={m['admin.publishing.hourLabel']()}
        options={hours}
        disabled={frequency === 'off'}
      />
      <Select
        id="publish-timezone"
        bind:selected={timezone}
        label={m['admin.publishing.timezoneLabel']()}
        options={timezones.map((zone) => ({ value: zone, label: zone }))}
        disabled={frequency === 'off'}
      />
    </div>

    <p class="fr-text--sm text-grey">
      {status.next_run_at
        ? m['admin.publishing.nextRun']({ date: formatDate(status.next_run_at) })
        : m['admin.publishing.nextRunNever']()}
    </p>

    <Button
      text={m['admin.publishing.save']()}
      disabled={busy}
      onclick={saveSchedule}
    />
  </section>

  <section>
    <h2 class="fr-h6">{m['admin.publishing.lastRun']()}</h2>

    {#if !status.last_run}
      <p class="fr-text--sm text-grey">{m['admin.publishing.lastRunNever']()}</p>
    {:else}
      {@const last = status.last_run}
      <Alert
        title={last.finished_at === null
          ? m['admin.publishing.runRunning']({ date: formatDate(last.started_at) })
          : last.succeeded
            ? m['admin.publishing.runSucceeded']({ date: formatDate(last.finished_at) })
            : m['admin.publishing.runFailed']({ date: formatDate(last.finished_at) })}
        variant={last.finished_at === null ? 'info' : last.succeeded ? 'success' : 'error'}
      >
        {#if last.error}
          <p class="fr-text--sm">{last.error}</p>
        {/if}
        <p class="fr-text--sm mb-0!">
          {last.published === null || last.held_back === null
            ? m['admin.publishing.runCountsUnknown']()
            : m['admin.publishing.runCounts']({
                published: last.published,
                heldBack: last.held_back
              })}
        </p>
      </Alert>
    {/if}
  </section>
</PageLayout>

<Modal
  id="fr-modal-destination"
  titleId="fr-modal-title-destination"
  headerClass="md:absolute! md:top-4 md:right-8 md:z-10 md:p-0!"
  contentClass="md:pt-4! mb-6!"
>
  <h2 id="fr-modal-title-destination" class="fr-modal__title">
    {editing ? m['admin.publishing.editTitle']() : m['admin.publishing.addTitle']()}
  </h2>

  <form onsubmit={submit}>
    <Input
      id="destination-name"
      bind:value={formName}
      label={m['admin.publishing.nameLabel']()}
      maxlength={100}
    />

    <Select
      id="destination-kind"
      bind:selected={formKind}
      label={m['admin.publishing.kindLabel']()}
      options={[
        { value: 'huggingface', label: m['admin.publishing.kindHuggingface']() },
        { value: 's3', label: m['admin.publishing.kindS3']() }
      ]}
    />

    {#if formKind === 'huggingface'}
      <Input
        id="destination-repo-path"
        bind:value={formRepoPath}
        label={m['admin.publishing.repoPathLabel']()}
        help={m['admin.publishing.repoPathHelp']()}
      />
      <Input
        id="destination-token"
        bind:value={formToken}
        type="password"
        label={m['admin.publishing.tokenLabel']()}
        help={editing
          ? m['admin.publishing.tokenKeep']()
          : m['admin.publishing.tokenHelp']()}
      />
    {:else}
      <Input
        id="destination-endpoint"
        bind:value={formEndpoint}
        label={m['admin.publishing.endpointLabel']()}
        help={m['admin.publishing.endpointHelp']()}
      />
      <Input
        id="destination-bucket"
        bind:value={formBucket}
        label={m['admin.publishing.bucketLabel']()}
      />
      <Input
        id="destination-region"
        bind:value={formRegion}
        label={m['admin.publishing.regionLabel']()}
      />
      <Input
        id="destination-prefix"
        bind:value={formPrefix}
        label={m['admin.publishing.prefixLabel']()}
        help={m['admin.publishing.prefixHelp']()}
      />
      <Toggle
        id="destination-secure"
        bind:value={formSecure}
        label={m['admin.publishing.secureLabel']()}
      />
      <Input
        id="destination-access-key"
        bind:value={formAccessKey}
        label={m['admin.publishing.accessKeyLabel']()}
        help={editing ? m['admin.publishing.secretKeep']() : undefined}
      />
      <Input
        id="destination-secret-key"
        bind:value={formSecretKey}
        type="password"
        label={m['admin.publishing.secretKeyLabel']()}
        help={editing ? m['admin.publishing.secretKeep']() : undefined}
      />
    {/if}

    <fieldset class="fr-fieldset mb-0">
      <legend class="fr-fieldset__legend fr-text--regular">
        {m['admin.publishing.datasetsLabel']()}
      </legend>
      <Checkbox
        id="destination-dataset-normal"
        bind:checked={wantsOpen}
        label={m['admin.publishing.datasetNormal']()}
        help={m['admin.publishing.datasetNormalHelp']()}
      />
      <Checkbox
        id="destination-dataset-raw"
        bind:checked={wantsRaw}
        label={m['admin.publishing.datasetRaw']()}
        help={m['admin.publishing.datasetRawHelp']()}
      />
    </fieldset>

    {#if wantsRaw}
      <Alert
        title={m['admin.publishing.datasetRaw']()}
        variant="warning"
        class="my-4"
      >
        <p class="fr-text--sm mb-0!">{m['admin.publishing.rawWarning']()}</p>
      </Alert>
    {/if}

    <Toggle
      id="destination-enabled"
      bind:value={formEnabled}
      label={m['admin.publishing.enabledLabel']()}
    />

    {#if formError}
      <p class="fr-error-text" aria-live="polite">{formError}</p>
    {/if}

    <div class="mt-6 gap-4 sm:flex-row sm:justify-end flex flex-col-reverse">
      <Button
        type="button"
        variant="secondary"
        text={m['admin.publishing.cancel']()}
        onclick={() => closeModal('fr-modal-destination')}
      />
      <Button type="submit" disabled={busy} text={m['admin.publishing.save']()} />
    </div>
  </form>
</Modal>

<Modal
  id="fr-modal-destination-delete"
  titleId="fr-modal-title-destination-delete"
  headerClass="md:absolute! md:top-4 md:right-8 md:z-10 md:p-0!"
  contentClass="md:pt-4! mb-6!"
>
  <h2 id="fr-modal-title-destination-delete" class="fr-modal__title">
    {m['admin.publishing.deleteConfirm']({ name: toDelete?.name ?? '' })}
  </h2>
  <p>{m['admin.publishing.deleteWarning']()}</p>

  <div class="mt-6 gap-4 sm:flex-row sm:justify-end flex flex-col-reverse">
    <Button
      variant="secondary"
      text={m['admin.publishing.cancel']()}
      disabled={busy}
      onclick={() => closeModal('fr-modal-destination-delete')}
    />
    <Button text={m['admin.publishing.delete']()} disabled={busy} onclick={confirmDelete} />
  </div>
</Modal>
