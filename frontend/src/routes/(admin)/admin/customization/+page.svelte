<script lang="ts">
  import { Button, Input } from '$components/dsfr'
  import ColorInput from '$components/form/ColorInput.svelte'
  import PageLayout from '$components/PageLayout.svelte'
  import { getAuthContext } from '$lib/auth.svelte'
  import { api } from '$lib/fastapi-client'
  import type { AppSettingsPatch, AppSettingsPublic } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { contrastRatio } from '$lib/theme'
  import { onMount } from 'svelte'

  let loading = $state(true)
  let saving = $state(false)
  let uploadingLogo = $state(false)

  let votesObjective = $state('')
  let platformName = $state('')
  let hasCustomLogo = $state(false)
  let logoVersion = $state(0)
  let primaryColorLight = $state('')
  let primaryColorDark = $state('')
  let secondaryColorLight = $state('')
  let secondaryColorDark = $state('')
  let homepageUrl = $state('')
  let loadedValues = $state({
    votesObjective: '',
    platformName: '',
    primaryColorLight: '',
    primaryColorDark: '',
    secondaryColorLight: '',
    secondaryColorDark: '',
    homepageUrl: ''
  })
  let errors = $state<Record<string, string>>({})

  const logoSrc = $derived(
    hasCustomLogo ? `${api.getUrl('/auth/config/logo')}?v=${logoVersion}` : '/orgs/comparia.png'
  )
  const auth = getAuthContext()

  async function load() {
    loading = true
    try {
      const data = await api.request<AppSettingsPublic>('/admin/settings')
      votesObjective = String(data.votes_objective)
      platformName = data.platform_name
      hasCustomLogo = data.has_custom_logo
      primaryColorLight = data.primary_color_light
      primaryColorDark = data.primary_color_dark
      secondaryColorLight = data.secondary_color_light
      secondaryColorDark = data.secondary_color_dark
      homepageUrl = data.homepage_url ?? ''
      loadedValues = { ...currentValues(), votesObjective, platformName }
    } finally {
      loading = false
    }
  }

  onMount(load)

  function currentValues() {
    return {
      primaryColorLight,
      primaryColorDark,
      secondaryColorLight,
      secondaryColorDark,
      homepageUrl
    }
  }

  function validate() {
    const nextErrors: Record<string, string> = {}
    const hexError = m['admin.settings.customization.colors.invalid']()
    for (const [field, value] of Object.entries(currentValues()).filter(
      ([field]) => field !== 'homepageUrl'
    )) {
      if (!/^#[0-9A-Fa-f]{6}$/.test(value)) nextErrors[field] = hexError
    }
    if (!nextErrors.primaryColorLight && contrastRatio(primaryColorLight, '#FFFFFF') < 4.5) {
      nextErrors.primaryColorLight = m['admin.settings.customization.colors.contrastLight']()
    }
    if (!nextErrors.primaryColorDark && contrastRatio(primaryColorDark, '#161616') < 4.5) {
      nextErrors.primaryColorDark = m['admin.settings.customization.colors.contrastDark']()
    }
    if (homepageUrl) {
      try {
        const url = new URL(homepageUrl)
        if (
          url.protocol !== 'https:' ||
          url.username ||
          url.password ||
          /\s/.test(homepageUrl.trim())
        )
          nextErrors.homepageUrl = m['admin.settings.customization.homepageUrl.invalid']()
      } catch {
        nextErrors.homepageUrl = m['admin.settings.customization.homepageUrl.invalid']()
      }
    }
    errors = nextErrors
    return Object.keys(nextErrors).length === 0
  }

  function discardChanges() {
    votesObjective = loadedValues.votesObjective
    platformName = loadedValues.platformName
    primaryColorLight = loadedValues.primaryColorLight
    primaryColorDark = loadedValues.primaryColorDark
    secondaryColorLight = loadedValues.secondaryColorLight
    secondaryColorDark = loadedValues.secondaryColorDark
    homepageUrl = loadedValues.homepageUrl
    errors = {}
  }

  async function save(e: SubmitEvent) {
    e.preventDefault()
    if (!validate()) return
    saving = true
    try {
      const patch: AppSettingsPatch = {
        votes_objective: Number(votesObjective),
        platform_name: platformName,
        primary_color_light: primaryColorLight.toUpperCase(),
        primary_color_dark: primaryColorDark.toUpperCase(),
        secondary_color_light: secondaryColorLight.toUpperCase(),
        secondary_color_dark: secondaryColorDark.toUpperCase(),
        homepage_url: homepageUrl || null
      }
      const saved = await api.request<AppSettingsPublic>('/admin/settings', {
        method: 'PATCH',
        body: JSON.stringify(patch)
      })
      platformName = saved.platform_name
      primaryColorLight = saved.primary_color_light
      primaryColorDark = saved.primary_color_dark
      secondaryColorLight = saved.secondary_color_light
      secondaryColorDark = saved.secondary_color_dark
      homepageUrl = saved.homepage_url ?? ''
      loadedValues = { ...currentValues(), votesObjective, platformName }
      Object.assign(auth.config, {
        platform_name: saved.platform_name,
        primary_color_light: saved.primary_color_light,
        primary_color_dark: saved.primary_color_dark,
        secondary_color_light: saved.secondary_color_light,
        secondary_color_dark: saved.secondary_color_dark,
        homepage_url: saved.homepage_url
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
      auth.config.has_custom_logo = true
      logoVersion++
      useToast(m['admin.settings.customization.logo.updated'](), 4000)
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
      auth.config.has_custom_logo = false
      useToast(m['admin.settings.customization.logo.resetDone'](), 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      uploadingLogo = false
    }
  }
</script>

<PageLayout
  seoTitle={m['admin.nav.customization']()}
  title={m['admin.nav.customization']()}
  subtitle={m['admin.settings.subtitle']()}
>
  {#if loading}
    <p class="fr-text--sm text-[--text-mention-grey]">{m['admin.settings.loading']()}</p>
  {:else}
    <form onsubmit={save} class="max-w-[720px]">
      <Input
        id="settings-platform-name"
        label={m['admin.settings.customization.platformName']()}
        bind:value={platformName}
        groupClass="mt-4!"
      />

      <Input
        id="settings-homepage-url"
        type="url"
        label={m['admin.settings.customization.homepageUrl.label']()}
        help={m['admin.settings.customization.homepageUrl.hint']()}
        bind:value={homepageUrl}
        error={errors.homepageUrl}
        disabled={saving}
        autocomplete="url"
        placeholder="https://example.gouv.fr"
        groupClass="mt-8!"
      />

      <div class="mt-4!">
        <p class="fr-label mb-2!">{m['admin.settings.customization.logo.label']()}</p>
        <div class="gap-4 flex items-center">
          <img
            src={logoSrc}
            alt=""
            class="bg-white h-[48px] border border-[--border-default-grey]"
          />
          <div class="gap-2 flex flex-col">
            <label class="fr-label">
              <span class="fr-sr-only">{m['admin.settings.customization.logo.chooseFile']()}</span>
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
                text={m['admin.settings.customization.logo.reset']()}
                disabled={uploadingLogo}
                onclick={resetLogo}
              />
            {/if}
          </div>
        </div>
        <p class="fr-hint-text mt-1!">{m['admin.settings.customization.logo.hint']()}</p>
      </div>

      <fieldset class="mt-8! p-0 border-0">
        <legend class="fr-h4">{m['admin.settings.customization.colors.title']()}</legend>
        <p class="fr-hint-text mt-0!">{m['admin.settings.customization.colors.hint']()}</p>
        <div class="gap-x-6 gap-y-4 md:grid-cols-2 grid">
          <ColorInput
            id="settings-primary-color-light"
            label={m['admin.settings.customization.colors.primaryLight']()}
            hint={m['admin.settings.customization.colors.fieldHint']()}
            bind:value={primaryColorLight}
            error={errors.primaryColorLight}
            disabled={saving}
          />
          <ColorInput
            id="settings-primary-color-dark"
            label={m['admin.settings.customization.colors.primaryDark']()}
            hint={m['admin.settings.customization.colors.fieldHint']()}
            bind:value={primaryColorDark}
            error={errors.primaryColorDark}
            disabled={saving}
          />
          <ColorInput
            id="settings-secondary-color-light"
            label={m['admin.settings.customization.colors.secondaryLight']()}
            hint={m['admin.settings.customization.colors.fieldHint']()}
            bind:value={secondaryColorLight}
            error={errors.secondaryColorLight}
            disabled={saving}
          />
          <ColorInput
            id="settings-secondary-color-dark"
            label={m['admin.settings.customization.colors.secondaryDark']()}
            hint={m['admin.settings.customization.colors.fieldHint']()}
            bind:value={secondaryColorDark}
            error={errors.secondaryColorDark}
            disabled={saving}
          />
        </div>
      </fieldset>

      <Input
        id="settings-votes-objective"
        type="number"
        min="0"
        label={m['admin.settings.customization.votesObjective']()}
        bind:value={votesObjective}
        groupClass="mt-4!"
      />
      <div class="gap-3 mt-4! flex flex-wrap">
        <Button
          type="submit"
          text={saving ? m['admin.settings.saving']() : m['admin.settings.save']()}
          disabled={saving}
        />
        <Button
          type="button"
          variant="secondary"
          text={m['admin.settings.customization.discard']()}
          disabled={saving}
          onclick={discardChanges}
        />
      </div>
    </form>
  {/if}
</PageLayout>
