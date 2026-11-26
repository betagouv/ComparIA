<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Button, Textarea, Toggle } from '$components/dsfr'
  import Form from '$components/form/Form.svelte'
  import FormTranslate from '$components/form/FormTranslate.svelte'
  import { PageLayout } from '$components/layout'
  import UserPreview from '$components/UserPreview.svelte'
  import { api } from '$lib/fastapi-client'
  import type { AppSettingsPublic, CookieBanner } from '$lib/generated/admin'
  import { getLocalesContext } from '$lib/global.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { Locale } from '$lib/i18n/runtime'
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
  <Toggle
    id="cookie_banner_enabled"
    label={m['admin.legal.cookies.switchLabel']()}
    help={m['admin.legal.cookies.switchHelp']()}
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
