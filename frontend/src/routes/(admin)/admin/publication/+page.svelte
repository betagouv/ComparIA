<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Badge, Button, Icon, Modal, Table } from '$components/dsfr'
  import { PageLayout } from '$components/layout'
  import { api, type ApiError } from '$lib/fastapi-client'
  import type { AdminPublishDestination } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { TableCol } from '$lib/utils/data'
  import type { PageProps } from './$types'
  import { DestinationForm, Overview, ReservationManagement, ReviewerSettings } from './components'
  import { formatDate, runStatus, runVariant, type Run } from './components/format'
  import { closeModal } from './components/modal'

  let { data }: PageProps = $props()

  const refetch = () => invalidate('admin:publishing')

  type Frequency = AdminPublishDestination['publish_frequency']

  const destinations = $derived(data.destinations.destinations)
  const status = $derived(data.status)
  const historyRows = $derived(status.runs.map((run) => ({ ...run, id: run.started_at })))

  const cols = [
    { id: 'name', label: m['admin.publishing.colName']() },
    { id: 'kind', label: m['admin.publishing.colKind']() },
    { id: 'target', label: m['admin.publishing.colTarget']() },
    { id: 'datasets', label: m['admin.publishing.colDatasets']() },
    { id: 'frequency', label: m['admin.publishing.frequencyLabel']() },
    { id: 'status', label: m['admin.publishing.colStatus']() },
    { id: 'actions', label: m['admin.publishing.colActions']() }
  ] satisfies TableCol[]

  const historyCols = [
    { id: 'date', label: m['admin.publishing.historyDate']() },
    { id: 'status', label: m['admin.publishing.historyStatus']() },
    { id: 'details', label: m['admin.publishing.historyDetails']() },
    { id: 'result', label: m['admin.publishing.historyResult']() }
  ] satisfies TableCol[]

  let busy = $state(false)
  let publishing = $state<string>()
  let toDelete = $state<AdminPublishDestination>()
  let form = $state<ReturnType<typeof DestinationForm>>()

  async function run(action: () => Promise<unknown>, success: string) {
    busy = true
    try {
      await action()
      useToast(success, 4000)
      await refetch()
      return true
    } catch (error) {
      useToast((error as ApiError).message, 6000, 'error')
      return false
    } finally {
      busy = false
    }
  }

  async function publishNow(destination: AdminPublishDestination) {
    publishing = destination.id
    try {
      await api.request(`/admin/publishing/destinations/${destination.id}/publish`, {
        method: 'POST'
      })
      useToast(m['admin.publishing.publishStarted'](), 4000)
      setTimeout(() => refetch(), 3000)
    } catch (error) {
      useToast((error as ApiError).message, 8000, 'error')
    } finally {
      publishing = undefined
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
            enabled,
            publish_frequency: destination.publish_frequency
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

  function target(destination: AdminPublishDestination) {
    const config = destination.config as Record<string, unknown>
    if (destination.kind === 'huggingface') return String(config.repo_path ?? '')
    const prefix = String(config.prefix ?? '')
    return `${config.bucket}${prefix ? `/${prefix}` : ''} · ${config.endpoint}`
  }

  const datasets = {
    normal: { label: m['admin.publishing.datasetNormal'](), variant: 'blue-ecume' },
    raw: { label: m['admin.publishing.datasetRaw'](), variant: 'orange' },
    reserved: { label: m['admin.publishing.datasetReserved'](), variant: 'purple' }
  } as const

  const frequencyLabel = (frequency: Frequency) =>
    ({
      off: m['admin.publishing.frequencyOff'](),
      daily: m['admin.publishing.frequencyDaily'](),
      weekly: m['admin.publishing.frequencyWeekly'](),
      monthly: m['admin.publishing.frequencyMonthly']()
    })[frequency]

  function formatPending(seconds: number) {
    const minutes = Math.floor(seconds / 60)
    if (minutes < 1) return '< 1 min'
    if (minutes < 60) return `${minutes} min`
    const hours = Math.floor(minutes / 60)
    return hours < 48 ? `${hours} h` : `${Math.floor(hours / 24)} d`
  }

  function runDetails(run: Run) {
    if (run.finished_at === null) return m['admin.publishing.historyPending']()
    if (!run.error) return m['admin.publishing.historyNoError']()
    if (run.error === 'No rows produced, aborting export') {
      return m['admin.publishing.historyNoRows']()
    }
    return m['admin.publishing.historyTechnicalError']()
  }

  function runResult(run: Run) {
    if (run.finished_at === null) return m['admin.publishing.historyPending']()
    if (!run.succeeded) return m['admin.publishing.historyNoDataset']()
    const counts =
      run.published === null || run.held_back === null
        ? m['admin.publishing.runCountsUnknown']()
        : m['admin.publishing.runCounts']({ published: run.published, heldBack: run.held_back })
    return run.reserved === null
      ? counts
      : `${counts} ${m['admin.publishing.runReserved']({ reserved: run.reserved })}`
  }
</script>

<PageLayout
  seoTitle={m['admin.publishing.title']()}
  title={m['admin.publishing.title']()}
  subtitle={m['admin.publishing.subtitle']()}
>
  <Overview {status} {destinations} />

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
          onclick={() => form?.open()}
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
              <Badge size="sm" text={datasets[dataset].label} variant={datasets[dataset].variant} />
            {/each}
          </span>
        {:else if col.id === 'frequency'}
          <span>
            {frequencyLabel(row.publish_frequency)}
            {#if row.next_run_at}
              <small class="text-grey block">
                {m['admin.publishing.nextRun']({ date: formatDate(row.next_run_at) })}
              </small>
            {/if}
            {#if row.request_pending_seconds != null}
              <small class="text-grey block">
                {m['admin.publishing.requestPending']({
                  duration: formatPending(row.request_pending_seconds)
                })}
              </small>
            {/if}
          </span>
        {:else if col.id === 'status'}
          <Badge
            size="sm"
            text={row.enabled ? m['admin.publishing.enabled']() : m['admin.publishing.disabled']()}
            variant={row.enabled ? 'green' : ''}
          />
        {:else if col.id === 'actions'}
          <span class="gap-1 flex justify-end">
            <Button
              size="sm"
              variant="secondary"
              text={publishing === row.id
                ? m['admin.publishing.publishing']()
                : m['admin.publishing.publishNow']()}
              disabled={busy || publishing === row.id || !row.enabled}
              aria-label={`${m['admin.publishing.publishNow']()} : ${row.name}`}
              onclick={() => publishNow(row)}
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
              onclick={() => form?.open(row)}
            >
              <Icon icon="i-ri-edit-line" />
            </Button>
            <Button
              size="sm"
              variant="tertiary-no-outline"
              iconOnly
              title={row.enabled ? m['admin.publishing.disable']() : m['admin.publishing.enable']()}
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
    <h2 class="fr-h6">{m['admin.publishing.lastRun']()}</h2>

    {#if !status.runs.length}
      <p class="fr-text--sm text-grey">{m['admin.publishing.lastRunNever']()}</p>
    {:else}
      <Table
        caption={m['admin.publishing.lastRun']()}
        hideCaption
        class="publication-history-table"
        cols={historyCols}
        rows={historyRows}
      >
        {#snippet cell(run, col)}
          {#if col.id === 'date'}
            {formatDate(run.finished_at ?? run.started_at)}
          {:else if col.id === 'status'}
            <Badge size="sm" text={runStatus(run)} variant={runVariant(run)} />
          {:else if col.id === 'details'}
            <span class="fr-text--sm">{runDetails(run)}</span>
          {:else if col.id === 'result'}
            <span class="fr-text--sm">{runResult(run)}</span>
          {/if}
        {/snippet}
      </Table>
    {/if}
  </section>

  <ReviewerSettings settings={data.settings} endpoints={data.endpoints} onsaved={refetch} />

  <ReservationManagement {status} onreleased={refetch} />
</PageLayout>

<DestinationForm bind:this={form} onsaved={refetch} />

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

<style>
  /* DSFR draws table separators as backgrounds; reinforce them here so the
     first history row remains separated in horizontally scrollable tables. */
  :global(.publication-history-table tbody tr:not(:last-child) td) {
    box-shadow: inset 0 -1px 0 var(--border-contrast-grey);
  }
</style>
