<script lang="ts">
  import { Button, Input, Select } from '$components/dsfr'
  import { api, type ApiError } from '$lib/fastapi-client'
  import type { AppSettingsPublic, LLMEndpoint } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { untrack } from 'svelte'

  let {
    settings,
    endpoints,
    onsaved
  }: {
    settings: AppSettingsPublic
    endpoints: LLMEndpoint[]
    onsaved: () => Promise<void>
  } = $props()

  let busy = $state(false)
  let endpointId = $state(untrack(() => settings.analysis_endpoint_id ?? ''))
  let model = $state(untrack(() => settings.analysis_model ?? ''))
  let error = $state<string>()

  async function save(event: SubmitEvent) {
    event.preventDefault()
    error = undefined
    const trimmed = model.trim()
    if (!endpointId !== !trimmed) {
      error = m['admin.publishing.reviewerIncomplete']()
      return
    }
    busy = true
    try {
      await api.request('/admin/settings', {
        method: 'PATCH',
        body: JSON.stringify({
          analysis_endpoint_id: endpointId || null,
          analysis_model: trimmed || null
        })
      })
      model = trimmed
      useToast(m['admin.publishing.reviewerSuccess'](), 4000)
      await onsaved()
    } catch (caught) {
      error = (caught as ApiError).message
    } finally {
      busy = false
    }
  }
</script>

<section class="mb-10">
  <h2 class="fr-h6 mb-2!">{m['admin.publishing.settingsTitle']()}</h2>
  <h3 class="fr-text--md font-bold mb-1!">{m['admin.publishing.reviewerTitle']()}</h3>
  <p class="fr-text--sm text-grey mb-4!">
    {m['admin.publishing.reviewerHelp']()}
    {m['admin.publishing.reviewerModelHelp']()}
  </p>

  <form onsubmit={save}>
    <div class="gap-4 md:grid-cols-2 grid">
      <Select
        id="reviewer-endpoint"
        bind:selected={endpointId}
        label={m['admin.publishing.reviewerEndpointLabel']()}
        options={[
          { value: '', label: m['admin.publishing.reviewerEndpointNone']() },
          ...endpoints
            .filter((endpoint) => endpoint.id)
            .map((endpoint) => ({ value: endpoint.id!, label: endpoint.name }))
        ]}
      />
      <Input
        id="reviewer-model"
        bind:value={model}
        label={m['admin.publishing.reviewerModelLabel']()}
      />
    </div>

    {#if error}
      <p class="fr-error-text" aria-live="polite">{error}</p>
    {/if}

    <div class="flex justify-start">
      <Button
        type="submit"
        variant="secondary"
        text={m['admin.publishing.reviewerSave']()}
        disabled={busy}
      />
    </div>
  </form>
</section>
