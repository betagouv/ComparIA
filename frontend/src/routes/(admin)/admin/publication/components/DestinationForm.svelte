<script lang="ts">
  import { Button, Checkbox, Input, Modal, Select, Toggle } from '$components/dsfr'
  import { api, type ApiError } from '$lib/fastapi-client'
  import type { AdminPublishDestination } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { closeModal, discloseModal } from './modal'

  let { onsaved }: { onsaved: () => Promise<void> } = $props()

  type Kind = 'huggingface' | 's3'
  type Dataset = AdminPublishDestination['datasets'][number]
  type Frequency = AdminPublishDestination['publish_frequency']
  // The open and reserved datasets never go to the same place, so a
  // destination picks one of them. Raw comes on top, or alone.
  type Main = 'normal' | 'reserved' | 'none'

  const MODAL_ID = 'fr-modal-destination'

  let busy = $state(false)
  let editing = $state<AdminPublishDestination>()
  let datasetsError = $state<string>()
  let formError = $state<string>()

  let name = $state('')
  let kind = $state<Kind>('huggingface')
  let main = $state<Main>('normal')
  let wantsRaw = $state(false)
  const datasets = $derived<Dataset[]>([
    ...(main === 'none' ? [] : [main]),
    ...(wantsRaw ? (['raw'] as const) : [])
  ])
  let enabled = $state(true)
  let frequency = $state<Frequency>('off')
  let repoPath = $state('')
  let token = $state('')
  let endpoint = $state('')
  let bucket = $state('')
  let region = $state('')
  let prefix = $state('')
  let secure = $state(true)
  let accessKey = $state('')
  let secretKey = $state('')

  const mainOptions = [
    {
      value: 'normal',
      label: m['admin.publishing.datasetNormal'](),
      help: m['admin.publishing.datasetNormalHelp']()
    },
    {
      value: 'reserved',
      label: m['admin.publishing.datasetReserved'](),
      help: m['admin.publishing.datasetReservedHelp']()
    },
    {
      value: 'none',
      label: m['admin.publishing.datasetNone'](),
      help: m['admin.publishing.datasetNoneHelp']()
    }
  ] as const

  /** Open the form on a destination, or empty to add one. */
  export function open(destination?: AdminPublishDestination) {
    editing = destination
    datasetsError = undefined
    formError = undefined
    const config = (destination?.config ?? {}) as Record<string, unknown>
    name = destination?.name ?? ''
    kind = destination?.kind ?? 'huggingface'
    main = !destination
      ? 'normal'
      : destination.datasets.includes('normal')
        ? 'normal'
        : destination.datasets.includes('reserved')
          ? 'reserved'
          : 'none'
    wantsRaw = destination?.datasets.includes('raw') ?? false
    enabled = destination?.enabled ?? true
    frequency = destination?.publish_frequency ?? 'off'
    // The secrets never come back from the API, so their fields start empty
    // and an empty field means 'keep the one already stored'.
    token = ''
    accessKey = ''
    secretKey = ''
    repoPath = String(config.repo_path ?? '')
    endpoint = String(config.endpoint ?? '')
    bucket = String(config.bucket ?? '')
    region = String(config.region ?? '')
    prefix = String(config.prefix ?? '')
    secure = config.secure !== false
    discloseModal(MODAL_ID)
  }

  function configPayload() {
    if (kind === 'huggingface') {
      return {
        kind: 'huggingface',
        repo_path: repoPath.trim(),
        ...(token.trim() ? { token: token.trim() } : {})
      }
    }
    return {
      kind: 's3',
      endpoint: endpoint.trim(),
      bucket: bucket.trim(),
      region: region.trim() || null,
      prefix: prefix.trim(),
      secure,
      ...(accessKey.trim() ? { access_key: accessKey.trim() } : {}),
      ...(secretKey.trim() ? { secret_key: secretKey.trim() } : {})
    }
  }

  async function submit(event: SubmitEvent) {
    event.preventDefault()
    formError = undefined
    datasetsError = datasets.length ? undefined : m['admin.publishing.datasetsError']()
    if (datasetsError) {
      document.getElementById('destination-dataset-normal')?.focus()
      return
    }

    const body = JSON.stringify({
      name: name.trim(),
      config: configPayload(),
      datasets,
      enabled,
      publish_frequency: frequency
    })
    const target = editing
    busy = true
    try {
      await (target
        ? api.request(`/admin/publishing/destinations/${target.id}`, { method: 'PUT', body })
        : api.request('/admin/publishing/destinations', { method: 'POST', body }))
      useToast(
        target ? m['admin.publishing.editSuccess']() : m['admin.publishing.createSuccess'](),
        4000
      )
      closeModal(MODAL_ID)
      await onsaved()
    } catch (error) {
      formError = (error as ApiError).message
    } finally {
      busy = false
    }
  }
</script>

<Modal
  id={MODAL_ID}
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
      bind:value={name}
      label={m['admin.publishing.nameLabel']()}
      maxlength={100}
    />

    <Select
      id="destination-kind"
      bind:selected={kind}
      label={m['admin.publishing.kindLabel']()}
      options={[
        { value: 'huggingface', label: m['admin.publishing.kindHuggingface']() },
        { value: 's3', label: m['admin.publishing.kindS3']() }
      ]}
    />

    {#if kind === 'huggingface'}
      <Input
        id="destination-repo-path"
        bind:value={repoPath}
        label={m['admin.publishing.repoPathLabel']()}
        help={m['admin.publishing.repoPathHelp']()}
      />
      <Input
        id="destination-token"
        bind:value={token}
        type="password"
        label={m['admin.publishing.tokenLabel']()}
        help={editing ? m['admin.publishing.tokenKeep']() : m['admin.publishing.tokenHelp']()}
      />
    {:else}
      <Input
        id="destination-endpoint"
        bind:value={endpoint}
        label={m['admin.publishing.endpointLabel']()}
        help={m['admin.publishing.endpointHelp']()}
      />
      <Input
        id="destination-bucket"
        bind:value={bucket}
        label={m['admin.publishing.bucketLabel']()}
      />
      <Input
        id="destination-region"
        bind:value={region}
        label={m['admin.publishing.regionLabel']()}
      />
      <Input
        id="destination-prefix"
        bind:value={prefix}
        label={m['admin.publishing.prefixLabel']()}
        help={m['admin.publishing.prefixHelp']()}
      />
      <Toggle
        id="destination-secure"
        bind:value={secure}
        label={m['admin.publishing.secureLabel']()}
      />
      <Input
        id="destination-access-key"
        bind:value={accessKey}
        label={m['admin.publishing.accessKeyLabel']()}
        help={editing ? m['admin.publishing.secretKeep']() : undefined}
      />
      <Input
        id="destination-secret-key"
        bind:value={secretKey}
        type="password"
        label={m['admin.publishing.secretKeyLabel']()}
        help={editing ? m['admin.publishing.secretKeep']() : undefined}
      />
    {/if}

    <fieldset
      class={['fr-fieldset', { 'fr-fieldset--error': !!datasetsError }]}
      aria-labelledby="destination-datasets-legend destination-datasets-messages"
    >
      <legend class="fr-fieldset__legend fr-text--regular" id="destination-datasets-legend">
        {m['admin.publishing.datasetsLabel']()}
        <span class="fr-hint-text">{m['admin.publishing.datasetsHelp']()}</span>
      </legend>
      {#each mainOptions as option (option.value)}
        <div class="fr-fieldset__element">
          <div class="fr-radio-group">
            <input
              id={`destination-dataset-${option.value}`}
              name="destination-dataset"
              type="radio"
              value={option.value}
              bind:group={main}
            />
            <label class="fr-label" for={`destination-dataset-${option.value}`}>
              {option.label}
              <span class="fr-hint-text">{option.help}</span>
            </label>
          </div>
        </div>
      {/each}
      <div class="fr-fieldset__element mt-2">
        <Checkbox
          id="destination-dataset-raw"
          bind:checked={wantsRaw}
          label={m['admin.publishing.datasetRaw']()}
          help={m['admin.publishing.datasetRawHelp']()}
        />
      </div>
      <div class="fr-messages-group" id="destination-datasets-messages" aria-live="polite">
        {#if datasetsError}
          <p class="fr-message fr-message--error">{datasetsError}</p>
        {/if}
        <!-- Who may see it is what matters once the dataset is chosen. -->
        {#if main === 'reserved'}
          <p class="fr-message fr-message--warning">{m['admin.publishing.reservedWarning']()}</p>
        {/if}
        {#if wantsRaw}
          <p class="fr-message fr-message--warning">{m['admin.publishing.rawWarning']()}</p>
        {/if}
      </div>
    </fieldset>

    <Select
      id="destination-publish-frequency"
      bind:selected={frequency}
      label={m['admin.publishing.frequencyLabel']()}
      help={frequency === 'off' ? undefined : m['admin.publishing.firstRunHelp']()}
      options={[
        { value: 'off', label: m['admin.publishing.frequencyOff']() },
        { value: 'daily', label: m['admin.publishing.frequencyDaily']() },
        { value: 'weekly', label: m['admin.publishing.frequencyWeekly']() },
        { value: 'monthly', label: m['admin.publishing.frequencyMonthly']() }
      ]}
    />

    <Toggle
      id="destination-enabled"
      bind:value={enabled}
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
        onclick={() => closeModal(MODAL_ID)}
      />
      <Button type="submit" disabled={busy} text={m['admin.publishing.save']()} />
    </div>
  </form>
</Modal>
