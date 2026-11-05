<script lang="ts">
  import { invalidateAll } from '$app/navigation'
  import { Button, Select } from '$components/dsfr'
  import { FormCheckboxGroup } from '$components/form'
  import { PageLayout } from '$components/layout'
  import { api } from '$lib/fastapi-client'
  import type { AppSettingsPatch, AppSettingsPublic } from '$lib/generated/admin'
  import { getLocalesContext } from '$lib/global.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  const locales = getLocalesContext()

  let loading = $state(true)
  let saving = $state(false)

  let enabledLocales = $state(locales.enabled)
  let defaultLocale = $state(locales.default)

  const defaultLocaleOptions = $derived(locales.asOptions(enabledLocales))

  $effect(() => {
    // Keep the selection valid if the admin unchecks the current default locale
    if (
      defaultLocaleOptions.length &&
      !defaultLocaleOptions.some((o) => o.value === defaultLocale)
    ) {
      defaultLocale = defaultLocaleOptions[0].value
    }
  })

  async function load() {
    loading = true
    try {
      const data = await api.request<AppSettingsPublic>('/admin/settings')
      enabledLocales = data.enabled_locales
      defaultLocale = data.default_locale
    } finally {
      loading = false
    }
  }

  onMount(load)

  async function save(e: SubmitEvent) {
    e.preventDefault()
    saving = true
    try {
      const patch: AppSettingsPatch = {
        enabled_locales: enabledLocales,
        default_locale: defaultLocale
      }
      await api.request('/admin/settings', { method: 'PATCH', body: JSON.stringify(patch) })
      useToast(m['admin.settings.saved'](), 4000)
      // Invalidate all since locales data are used almost everywhere
      await invalidateAll()
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      saving = false
    }
  }
</script>

<PageLayout
  seoTitle={m['admin.nav.locales']()}
  title={m['admin.nav.locales']()}
  subtitle={m['admin.settings.subtitle']()}
>
  {#if loading}
    <p class="fr-text--sm text-[--text-mention-grey]">{m['admin.settings.loading']()}</p>
  {:else}
    <form onsubmit={save} class="max-w-[480px]">
      <FormCheckboxGroup
        id="enabled_locales"
        label={m['admin.settings.locales.enabled.label']()}
        help={m['admin.settings.locales.enabled.hint']()}
        options={locales.allOptions}
        bind:value={enabledLocales}
      />

      <Select
        id="settings-default-locale"
        label={m['admin.settings.locales.default.label']()}
        bind:selected={defaultLocale}
        options={defaultLocaleOptions}
        groupClass="mt-4! max-w-[240px]"
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
