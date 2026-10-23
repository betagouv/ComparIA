<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Textarea } from '$components/dsfr'
  import { FormCheckboxGroup, FormInput, FormRadioGroup } from '$components/form'
  import Form from '$components/form/Form.svelte'
  import FormTranslate from '$components/form/FormTranslate.svelte'
  import { PageLayout } from '$components/layout'
  import { getAuthContext, getPlatformName } from '$lib/authContext.svelte'
  import { m } from '$lib/i18n/messages'
  import type {
    InformationalPageKey,
    InformationalPageSurface
  } from '$lib/informational-pages.svelte'
  import { useForm } from '$lib/stores/form.svelte'
  import type { PageProps } from './$types'

  const { data, params }: PageProps = $props()

  const auth = getAuthContext()
  const platformName = getPlatformName()
  const pageKey = $derived(params.infoPage as InformationalPageKey)
  const defaultLocale = $derived(auth.config.default_locale)
  let selectedLocale = $derived(defaultLocale)

  const form = $derived(
    useForm({
      url: `/admin/legal/informational-page/${pageKey}`,
      method: 'put',
      initialData: () => data.page,
      onBeforeSubmit: (form, errors) => {
        if (form.mode === 'internal' && !form.content_by_locale[defaultLocale]) {
          // FIXME show error in FormTranslate Segmented
          errors[`content_by_locale-${selectedLocale}`] = m['form.missing_default_locale']()
          return null
        }
        return form
      },
      onSuccess: async () => await invalidate('admin:legal')
    })
  )

  // Little trick to be able to use what should be toggles as checkbox group
  let showPageIn = $derived<{ value: Array<InformationalPageSurface> }>({
    get value() {
      return [
        form.form.visible_in_legal_menu ? ('legal_menu' as const) : null,
        form.form.visible_in_settings ? ('settings' as const) : null
      ].filter((v) => v !== null)
    },
    set value(value: InformationalPageSurface[]) {
      form.form.visible_in_legal_menu = value.includes('legal_menu')
      form.form.visible_in_settings = value.includes('settings')
    }
  })
</script>

<PageLayout
  seoTitle={m[`admin.legal.${pageKey}.title`]()}
  title={m[`admin.legal.${pageKey}.title`]()}
  subtitle={m[`admin.legal.${pageKey}.subtitle`]()}
  backLink={{ href: resolve('/admin/legal'), text: m['admin.legal.back']() }}
  noPadding
>
  <Form id="info-page" label={m[`admin.legal.${pageKey}.title`]()} {...form} stickyFooter>
    <FormRadioGroup
      id="mode"
      bind:value={form.form.mode}
      label={m['admin.legal.informational.modeLabel']()}
      options={[
        { value: 'internal', label: m['admin.legal.informational.internal']({ platformName }) },
        { value: 'external', label: m['admin.legal.informational.external']() }
      ]}
    />

    {#if form.form.mode === 'external'}
      <FormInput
        id="external_url"
        type="url"
        label={m['admin.legal.informational.externalUrl']()}
        help={m['admin.legal.informational.externalUrlHelp']()}
        errors={form.errors}
        required
        bind:value={form.form.external_url}
      />
    {:else}
      <FormTranslate
        id="content_by_locale"
        bind:value={form.form.content_by_locale}
        bind:locale={selectedLocale}
      >
        {#snippet subSnippet(locale, label)}
          <Textarea
            id="content_by_locale-{locale}"
            label={m['admin.legal.informational.contentLabel']({ locale: label })}
            help={m['admin.legal.markdownHelp']()}
            rows={12}
            error={form.errors[`content_by_locale-${locale}`]}
            bind:value={form.form.content_by_locale[locale]}
          />
        {/snippet}
      </FormTranslate>
    {/if}

    <FormCheckboxGroup
      id="show-in"
      label={m['admin.legal.informational.visibilityLabel']()}
      options={[
        { value: 'legal_menu', label: m['admin.legal.informational.visibleInLegalMenu']() },
        { value: 'settings', label: m['admin.legal.informational.visibleInSettings']() }
      ]}
      bind:value={showPageIn.value}
    />
  </Form>
</PageLayout>
