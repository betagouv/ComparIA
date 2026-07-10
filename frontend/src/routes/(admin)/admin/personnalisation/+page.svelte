<script lang="ts">
  import { Button, Input } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  interface AppSettings {
    votes_objective: number
    platform_name: string
    has_custom_logo: boolean
  }

  let loading = $state(true)
  let saving = $state(false)
  let uploadingLogo = $state(false)

  let votesObjective = $state('')
  let platformName = $state('')
  let hasCustomLogo = $state(false)
  let logoVersion = $state(0)

  const logoSrc = $derived(
    hasCustomLogo ? `${api.getUrl('/auth/config/logo')}?v=${logoVersion}` : '/orgs/comparia.png'
  )

  async function load() {
    loading = true
    try {
      const data = await api.request<AppSettings>('/admin/settings')
      votesObjective = String(data.votes_objective)
      platformName = data.platform_name
      hasCustomLogo = data.has_custom_logo
    } finally {
      loading = false
    }
  }

  onMount(load)

  async function save(e: SubmitEvent) {
    e.preventDefault()
    saving = true
    try {
      await api.request('/admin/settings', {
        method: 'PATCH',
        body: JSON.stringify({
          votes_objective: Number(votesObjective),
          platform_name: platformName
        })
      })
      useToast(m['admin.settings.saved'](), 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      saving = false
    }
  }

  async function uploadLogo(e: Event) {
    const input = e.currentTarget as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return

    uploadingLogo = true
    try {
      const formData = new FormData()
      formData.append('file', file)
      await api.request('/admin/settings/logo', { method: 'PUT', body: formData, headers: {} })
      hasCustomLogo = true
      logoVersion++
      useToast(m['admin.settings.personnalisation.logo.updated'](), 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      uploadingLogo = false
      input.value = ''
    }
  }

  async function resetLogo() {
    uploadingLogo = true
    try {
      await api.request('/admin/settings/logo', { method: 'DELETE', headers: {} })
      hasCustomLogo = false
      useToast(m['admin.settings.personnalisation.logo.resetDone'](), 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      uploadingLogo = false
    }
  }
</script>

<PageLayout
  seoTitle={m['admin.nav.personnalisation']()}
  title={m['admin.nav.personnalisation']()}
  subtitle={m['admin.settings.subtitle']()}
>
  {#if loading}
    <p class="fr-text--sm text-[--text-mention-grey]">{m['admin.settings.loading']()}</p>
  {:else}
    <form onsubmit={save} class="max-w-[480px]">
      <Input
        id="settings-platform-name"
        label={m['admin.settings.personnalisation.platformName']()}
        bind:value={platformName}
        groupClass="mt-4!"
      />
      <Input
        id="settings-votes-objective"
        type="number"
        min="0"
        label={m['admin.settings.personnalisation.votesObjective']()}
        bind:value={votesObjective}
        groupClass="mt-4!"
      />
      <Button
        type="submit"
        text={saving ? m['admin.settings.saving']() : m['admin.settings.save']()}
        disabled={saving}
        class="mt-4!"
      />
    </form>

    <div class="mt-8! max-w-[480px]">
      <p class="fr-label mb-2!">{m['admin.settings.personnalisation.logo.label']()}</p>
      <div class="gap-4 flex items-center">
        <img src={logoSrc} alt="" class="bg-white h-[48px] border border-[--border-default-grey]" />
        <div class="gap-2 flex flex-col">
          <label class="fr-label">
            <span class="fr-sr-only">{m['admin.settings.personnalisation.logo.chooseFile']()}</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/svg+xml,image/webp"
              disabled={uploadingLogo}
              onchange={uploadLogo}
            />
          </label>
          {#if hasCustomLogo}
            <Button
              type="button"
              variant="secondary"
              size="sm"
              text={m['admin.settings.personnalisation.logo.reset']()}
              disabled={uploadingLogo}
              onclick={resetLogo}
            />
          {/if}
        </div>
      </div>
      <p class="fr-hint-text mt-1!">{m['admin.settings.personnalisation.logo.hint']()}</p>
    </div>
  {/if}
</PageLayout>
