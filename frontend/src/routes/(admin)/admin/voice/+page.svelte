<script lang="ts">
  import { Button, Input, Textarea, Toggle } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api, ValidationError } from '$lib/fastapi-client'
  import type { VoiceSettingsPatch, VoiceSettingsPublic } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  let loading = $state(true)
  let saving = $state(false)

  let enabled = $state(false)
  let storeAudio = $state(false)
  // One model per line, which is how an admin reads a list of ten ids.
  let models = $state('')
  let apiKey = $state('')
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
      hasApiKey = data.has_api_key
      maxSeconds = String(data.max_seconds)
      retentionDays = data.retention_days ? String(data.retention_days) : ''
    } finally {
      loading = false
    }
  }

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
        max_seconds: Number(maxSeconds),
        retention_days: retentionDays ? Number(retentionDays) : null
      }
      // Left out unless the admin typed something, so saving the page does not
      // clear a stored key by sending an empty field back.
      if (apiKey) patch.api_key = apiKey

      const data = await api.request<VoiceSettingsPublic>('/admin/voice', {
        method: 'PATCH',
        body: JSON.stringify(patch)
      })
      hasApiKey = data.has_api_key
      apiKey = ''
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
      <Toggle id="voice-enabled" label={m['admin.voice.enabled.label']()} bind:value={enabled} />
      <p class="fr-hint-text mt-0! mb-4!">{m['admin.voice.enabled.hint']()}</p>

      <Toggle
        id="voice-store-audio"
        label={m['admin.voice.storeAudio.label']()}
        bind:value={storeAudio}
      />
      <p class="fr-hint-text mt-0! mb-4!">{m['admin.voice.storeAudio.hint']()}</p>

      <Textarea
        id="voice-models"
        label={m['admin.voice.models.label']()}
        help={m['admin.voice.models.hint']()}
        bind:value={models}
        rows={6}
      />

      <Input
        id="voice-max-seconds"
        type="number"
        label={m['admin.voice.maxSeconds.label']()}
        help={m['admin.voice.maxSeconds.hint']()}
        bind:value={maxSeconds}
        groupClass="max-w-[240px]"
      />

      <Input
        id="voice-retention-days"
        type="number"
        label={m['admin.voice.retentionDays.label']()}
        help={m['admin.voice.retentionDays.hint']()}
        bind:value={retentionDays}
        groupClass="max-w-[240px]"
      />

      <Input
        id="voice-api-key"
        type="password"
        label={m['admin.voice.apiKey.label']()}
        help={hasApiKey ? m['admin.voice.apiKey.set']() : m['admin.voice.apiKey.hint']()}
        bind:value={apiKey}
      />

      <Button
        type="submit"
        text={saving ? m['admin.settings.saving']() : m['admin.settings.save']()}
        disabled={saving}
        class="mt-4!"
      />
    </form>
  {/if}
</PageLayout>
