<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Button, Input, Textarea, Toggle } from '$components/dsfr'
  import { FormRadioGroup } from '$components/form'
  import Form from '$components/form/Form.svelte'
  import FormTranslate from '$components/form/FormTranslate.svelte'
  import { PageLayout } from '$components/layout'
  import UserPreview from '$components/UserPreview.svelte'
  import { api, type ApiError } from '$lib/fastapi-client'
  import type { AppSettingsPatch, AppSettingsPublic, CookieBanner } from '$lib/generated/admin'
  import { getLocalesContext } from '$lib/global.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { Locale } from '$lib/i18n/runtime'
  import { measurementInUse, type Measurement, type MeasurementSetting } from '$lib/matomo'
  import { useForm } from '$lib/stores/form.svelte'
  import { getKeys } from '$lib/utils/commons'
  import { CookieBannerPreview } from './components'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()

  const locales = getLocalesContext()

  // What the switch shows while its request is out, so it moves on click.
  let pending = $state<boolean>()
  // Kept here rather than reloaded, so that saving the switch leaves unsaved text alone.
  let saved = $state<boolean>()
  const enabled = $derived(pending ?? saved ?? data.settings.cookie_banner_enabled)

  async function setEnabled(enabled: boolean) {
    pending = enabled
    try {
      const settings = await api.request<AppSettingsPublic>('/admin/settings', {
        method: 'PATCH',
        body: JSON.stringify({ cookie_banner_enabled: enabled })
      })
      saved = settings.cookie_banner_enabled
      useToast(
        enabled ? m['admin.legal.cookies.switchedOn']() : m['admin.legal.cookies.switchedOff'](),
        4000,
        'success'
      )
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      pending = undefined
    }
  }

  // The radio group holds strings; null is the server setting, true is the
  // admin's own Matomo, false is Off.
  type MeasurementChoice = 'server' | 'on' | 'off'
  const toChoice = (setting: boolean | null): MeasurementChoice =>
    setting === null ? 'server' : setting ? 'on' : 'off'
  // Undefined until saved here. The switch and its notes follow the saved
  // setting, what visitors get, not a choice or typing not yet saved.
  let savedMatomo = $state<MeasurementSetting>()
  const matomoSetting = $derived(savedMatomo ?? data.settings)
  const measurementSetting = $derived(matomoSetting.matomo_enabled)
  const measurement = $derived(measurementInUse(matomoSetting, data.serverMatomo))
  let measurementChoice = $derived<MeasurementChoice>(toChoice(measurementSetting))
  // Off keeps the stored address and id, so On again shows them. Seeded once,
  // so that saving the banner text leaves unsaved typing alone.
  // svelte-ignore state_referenced_locally
  let matomoUrl = $state(data.settings.matomo_url ?? '')
  // svelte-ignore state_referenced_locally
  let matomoSiteId = $state(data.settings.matomo_site_id ?? '')
  let matomoErrors = $state<{ matomo_url?: string; matomo_site_id?: string }>({})

  const fieldErrors: Record<string, () => string> = {
    matomo_url_invalid: m['admin.legal.cookies.matomoUrlInvalid'],
    matomo_site_id_invalid: m['admin.legal.cookies.matomoSiteIdInvalid']
  }

  // The environment values are unchecked, so no URL parsing that could throw.
  const describe = (measurement: Measurement) =>
    measurement
      ? m['admin.legal.cookies.measurementServerOn']({
          address: measurement.url.replace(/^https?:\/\//, '').replace(/\/+$/, ''),
          id: measurement.id
        })
      : m['admin.legal.cookies.measurementServerNone']()
  const serverMeans = $derived(
    describe(
      measurementInUse(
        { matomo_enabled: null, matomo_url: null, matomo_site_id: null },
        data.serverMatomo
      )
    )
  )

  async function saveMeasurement(body: AppSettingsPatch) {
    matomoErrors = {}
    try {
      const settings = await api.request<AppSettingsPublic>('/admin/settings', {
        method: 'PATCH',
        body: JSON.stringify(body)
      })
      savedMatomo = {
        matomo_enabled: settings.matomo_enabled,
        matomo_url: settings.matomo_url,
        matomo_site_id: settings.matomo_site_id
      }
      // As stored: a trailing slash is dropped.
      matomoUrl = settings.matomo_url ?? ''
      matomoSiteId = settings.matomo_site_id ?? ''
      useToast(m['admin.legal.cookies.measurementSaved'](), 4000, 'success')
    } catch (error) {
      const { detail } = error as ApiError
      if (detail === 'matomo_needs_url_and_site_id') {
        const missing = m['admin.legal.cookies.matomoMissing']()
        matomoErrors = {
          matomo_url: matomoUrl.trim() ? undefined : missing,
          matomo_site_id: matomoSiteId.trim() ? undefined : missing
        }
      } else if (Array.isArray(detail)) {
        for (const { loc, type } of detail as { loc: string[]; type: string }[]) {
          const field = loc.at(-1) as keyof typeof matomoErrors
          if (fieldErrors[type]) matomoErrors[field] = fieldErrors[type]()
        }
      }
      if (!Object.values(matomoErrors).some(Boolean)) {
        useToast((error as Error).message, 6000, 'error')
      }
      if (body.matomo_enabled !== true) measurementChoice = toChoice(measurementSetting)
    }
  }

  // On waits for the address and site id; the other two save at once.
  function setMeasurement(choice: MeasurementChoice) {
    measurementChoice = choice
    if (choice !== 'on') saveMeasurement({ matomo_enabled: choice === 'off' ? false : null })
  }

  function switchOn(event: SubmitEvent) {
    event.preventDefault()
    saveMeasurement({
      matomo_enabled: true,
      matomo_url: matomoUrl.trim(),
      matomo_site_id: matomoSiteId.trim()
    })
  }

  const form = useForm({
    url: '/admin/legal/cookies',
    method: 'put',
    initialData: () => {
      const banners = structuredClone(data.banners)
      const currentLocales = getKeys(banners)
      locales.enabled
        .filter((locale) => !currentLocales.includes(locale))
        .forEach((locale) => {
          banners[locale] = {} as CookieBanner
        })
      return banners
    },
    onBeforeSubmit: (form) => {
      getKeys(form).forEach((k) => {
        // We need to clear an empty locale
        if (!Object.values(form[k]).some(Boolean)) delete form[k]
      })
      return form
    },
    onSuccess: async () => await invalidate('admin:legal')
  })

  function clearLocale(locale: Locale) {
    form.form[locale] = {} as CookieBanner
    Object.keys(form.errors).forEach((k) => {
      if (k.startsWith(locale)) delete form.errors[k]
    })
  }

  function isValid(locale: Locale) {
    const banner = form.form[locale]
    return !!banner && Object.values(banner).filter(Boolean).length === fields.length
  }

  const fields = [
    { key: 'title', label: m['admin.legal.cookies.bannerTitle'](), rows: 2, maxlength: 200 },
    { key: 'description', label: m['admin.legal.cookies.description'](), rows: 4, maxlength: 2000 }
  ] as const
</script>

<PageLayout
  seoTitle={m['admin.legal.cookies.title']()}
  title={m['admin.legal.cookies.title']()}
  subtitle={m['admin.legal.cookies.subtitle']()}
  backLink={{ href: resolve('/admin/legal'), text: m['admin.legal.back']() }}
  noPadding
>
  <FormRadioGroup
    id="matomo_enabled"
    label={m['admin.legal.cookies.measurementLabel']()}
    options={[
      {
        value: 'server',
        label: m['admin.legal.cookies.measurementServer'](),
        help: serverMeans
      },
      { value: 'on', label: m['admin.legal.cookies.measurementOn']() },
      { value: 'off', label: m['admin.legal.cookies.measurementOff']() }
    ]}
    bind:value={
      () => measurementChoice, (value) => value && setMeasurement(value as MeasurementChoice)
    }
  />

  {#if measurementChoice === 'on'}
    <form onsubmit={switchOn} class="mb-8! max-w-[720px]">
      <Input
        id="matomo_url"
        type="url"
        label={m['admin.legal.cookies.matomoUrlLabel']()}
        help={m['admin.legal.cookies.matomoUrlHint']()}
        placeholder="https://stats.example.org"
        bind:value={matomoUrl}
        error={matomoErrors.matomo_url}
      />
      <Input
        id="matomo_site_id"
        inputmode="numeric"
        label={m['admin.legal.cookies.matomoSiteIdLabel']()}
        help={m['admin.legal.cookies.matomoSiteIdHint']()}
        bind:value={matomoSiteId}
        error={matomoErrors.matomo_site_id}
      />
      <Button type="submit" text={m['admin.legal.cookies.measurementSwitchOn']()} />
    </form>
  {/if}

  <Toggle
    id="cookie_banner_enabled"
    label={m['admin.legal.cookies.switchLabel']()}
    help={measurement
      ? m['admin.legal.cookies.switchHelp']()
      : m['admin.legal.cookies.switchNothingToAsk']()}
    disabled={!measurement}
    labelPos="right"
    groupClass="mb-8!"
    bind:value={() => enabled, (value) => setEnabled(value)}
  />

  <Form id="cookies" label={m['admin.legal.cookies.formTitle']()} {...form} stickyFooter>
    <FormTranslate id="cookies-form" bind:value={form.form} {isValid}>
      {#snippet subSnippet(locale)}
        <Button
          icon="delete-bin-line"
          text={m['admin.legal.cookies.clearLocale']()}
          size="sm"
          class="ms-6"
          onclick={() => clearLocale(locale)}
        />

        <UserPreview id="cookies-preview" ratio="sm" class="mt-6">
          <p>{m['admin.legal.cookies.textDescription']()}</p>

          {#each fields as field, i (field.key)}
            <Textarea
              id="{locale}-{field.key}"
              label={field.label}
              groupClass={i ? 'fr-mt-4v' : undefined}
              rows={field.rows}
              maxlength={field.maxlength}
              required
              error={form.errors[`${locale}-${field.key}`]}
              bind:value={form.form[locale][field.key]}
            />
          {/each}

          {#snippet contentSnippet()}
            <CookieBannerPreview {...form.form[locale]} />
          {/snippet}
        </UserPreview>
      {/snippet}
    </FormTranslate>
  </Form>
</PageLayout>
