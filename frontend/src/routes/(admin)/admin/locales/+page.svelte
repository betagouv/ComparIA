<script lang="ts">
  import { Button, Checkbox, Select } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import type { AppSettingsPatch, AppSettingsPublic } from '$lib/generated/admin'
  import { ALL_LOCALES } from '$lib/global.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  let loading = $state(true)
  let saving = $state(false)

  let enabledLocales = $state<Record<string, boolean>>({})
  let defaultLocale = $state('')

  const defaultLocaleOptions = $derived(
    ALL_LOCALES.filter((locale) => enabledLocales[locale.code]).map((locale) => ({
      value: locale.code,
      label: locale.long
    }))
  )

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
      // Unchecking a locale takes it away from visitors already reading in it:
      // the next request rewrites their PARAGLIDE_LOCALE cookie to the default.
      enabledLocales = Object.fromEntries(
        ALL_LOCALES.map((locale) => [locale.code, data.enabled_locales?.includes(locale.code)])
      )
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
        enabled_locales: ALL_LOCALES.filter((locale) => enabledLocales[locale.code]).map(
          (locale) => locale.code
        ),
        default_locale: defaultLocale
      }
      await api.request('/admin/settings', { method: 'PATCH', body: JSON.stringify(patch) })
      useToast(m['admin.settings.saved'](), 4000)
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
      <div>
        <p class="fr-label mb-2!">{m['admin.settings.locales.enabled.label']()}</p>
        {#each ALL_LOCALES as locale (locale.code)}
          <Checkbox
            id="settings-locale-{locale.code}"
            label={locale.long}
            bind:checked={enabledLocales[locale.code]}
          />
        {/each}
      </div>

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
