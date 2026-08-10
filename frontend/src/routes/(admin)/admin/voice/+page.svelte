<script lang="ts">
  import { Button, Input, Select, Textarea, Toggle, Tooltip } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api, ValidationError } from '$lib/fastapi-client'
  import type {
    VoiceEndpointChoice,
    VoiceSettingsPatch,
    VoiceSettingsPublic
  } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  let loading = $state(true)
  let saving = $state(false)

  let enabled = $state(false)
  let storeAudio = $state(false)
  // One model per line, which is how an admin reads a list of ten ids.
  let models = $state('')
  let endpointId = $state('')
  let endpoints = $state<VoiceEndpointChoice[]>([])
  let hasApiKey = $state(false)
  let maxSeconds = $state('60')
  let retentionDays = $state('')

  async function load() {
    loading = true
    try {
      const data = await api.request<VoiceSettingsPublic>('/admin/voice')
      enabled = data.enabled
      storeAudio = data.store_audio
      models = data.models.join('\n')
      endpointId = data.endpoint_id ?? ''
      endpoints = data.endpoints ?? []
      hasApiKey = data.has_api_key
      maxSeconds = String(data.max_seconds)
      retentionDays = data.retention_days ? String(data.retention_days) : ''
    } finally {
      loading = false
    }
  }

  // An endpoint with no key cannot transcribe, so the panel says which is which
  // rather than letting someone pick one and wonder why nothing comes back.
  const endpointOptions = $derived([
    { value: '', label: m['admin.voice.endpoint.fromEnv']() },
    ...endpoints.map((e) => ({
      value: e.id,
      label: e.has_api_key
        ? `${e.name} (${e.api_type})`
        : m['admin.voice.endpoint.without']({ name: e.name })
    }))
  ])

  onMount(load)

  async function save(e: SubmitEvent) {
    e.preventDefault()
    saving = true
    try {
      const patch: VoiceSettingsPatch = {
        enabled,
        store_audio: storeAudio,
        models: models
          .split('\n')
          .map((model) => model.trim())
          .filter(Boolean),
        // Empty means no endpoint chosen, which falls back to the environment.
        endpoint_id: endpointId || null,
        max_seconds: Number(maxSeconds),
        retention_days: retentionDays ? Number(retentionDays) : null
      }

      const data = await api.request<VoiceSettingsPublic>('/admin/voice', {
        method: 'PATCH',
        body: JSON.stringify(patch)
      })
      endpointId = data.endpoint_id ?? ''
      endpoints = data.endpoints ?? []
      hasApiKey = data.has_api_key
      useToast(m['admin.settings.saved'](), 4000)
    } catch (err) {
      // A 422 carries the field message ("At least one model is needed"); the
      // Error itself only says "Error in form", which helps nobody.
      // Pydantic prefixes its own message with "Value error, ", which is
      // noise to an admin reading a toast.
      const validation = err instanceof ValidationError ? err.errors?.[0]?.msg : undefined
      useToast(validation?.replace(/^Value error, /, '') ?? (err as Error).message, 6000, 'error')
    } finally {
      saving = false
    }
  }
</script>

<PageLayout
  seoTitle={m['admin.nav.voice']()}
  title={m['admin.nav.voice']()}
  subtitle={m['admin.voice.subtitle']()}
>
  {#if loading}
    <p class="fr-text--sm text-[--text-mention-grey]">{m['admin.settings.loading']()}</p>
  {:else}
    <form onsubmit={save} class="max-w-[480px]">
      <Toggle
        id="voice-enabled"
        label={m['admin.voice.enabled.label']()}
        bind:value={enabled}
        inline={false}
        groupClass="mb-4"
      >
        {#snippet tooltip()}
          <Tooltip id="voice-enabled-help" text={m['admin.voice.enabled.hint']()} />
        {/snippet}
      </Toggle>

      <Toggle
        id="voice-store-audio"
        label={m['admin.voice.storeAudio.label']()}
        bind:value={storeAudio}
        inline={false}
        groupClass="mb-4"
      >
        {#snippet tooltip()}
          <Tooltip id="voice-store-audio-help" text={m['admin.voice.storeAudio.hint']()} />
        {/snippet}
      </Toggle>

      <Textarea
        id="voice-models"
        label={m['admin.voice.models.label']()}
        bind:value={models}
        rows={6}
      >
        {#snippet tooltip()}
          <Tooltip id="voice-models-help" text={m['admin.voice.models.hint']()} />
        {/snippet}
      </Textarea>

      <Input
        id="voice-max-seconds"
        type="number"
        label={m['admin.voice.maxSeconds.label']()}
        bind:value={maxSeconds}
        groupClass="w-[240px]"
      >
        {#snippet tooltip()}
          <Tooltip id="voice-max-seconds-help" text={m['admin.voice.maxSeconds.hint']()} />
        {/snippet}
      </Input>

      <Input
        id="voice-retention-days"
        type="number"
        label={m['admin.voice.retentionDays.label']()}
        bind:value={retentionDays}
        groupClass="w-[240px]"
      >
        {#snippet tooltip()}
          <Tooltip id="voice-retention-days-help" text={m['admin.voice.retentionDays.hint']()} />
        {/snippet}
      </Input>

      <Select
        id="voice-endpoint"
        label={m['admin.voice.endpoint.label']()}
        bind:selected={endpointId}
        options={endpointOptions}
        groupClass="w-[360px]"
      >
        {#snippet tooltip()}
          <Tooltip id="voice-endpoint-help" text={m['admin.voice.endpoint.hint']()} />
        {/snippet}
      </Select>

      {#if !hasApiKey}
        <!-- Not a hint. Without a key nothing transcribes, so it stays on screen
             rather than waiting behind a question mark. -->
        <p class="fr-message fr-message--error mb-4!">{m['admin.voice.endpoint.noKey']()}</p>
      {/if}

      <Button
        type="submit"
        text={saving ? m['admin.settings.saving']() : m['admin.settings.save']()}
        disabled={saving}
        class="mt-4!"
      />
    </form>
  {/if}
</PageLayout>
