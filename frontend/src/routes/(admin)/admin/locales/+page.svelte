<script lang="ts">
  import { invalidateAll } from '$app/navigation'
  import { FormCheckboxGroup, FormSelect } from '$components/form'
  import Form from '$components/form/Form.svelte'
  import { PageLayout } from '$components/layout'
  import { getLocalesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { useForm } from '$lib/stores/form.svelte'
  import { pick } from '$lib/utils/commons'
  import type { PageProps } from './$types'

  let { data }: PageProps = $props()

  const locales = getLocalesContext()

  const form = useForm({
    url: '/admin/settings',
    method: 'PATCH',
    initialData: () => pick(data.settings, ['enabled_locales', 'default_locale']),
    // Invalidate all since locales data are used almost everywhere
    onSuccess: async () => await invalidateAll()
  })

  const defaultLocaleOptions = $derived(locales.asOptions(form.form.enabled_locales))

  $effect(() => {
    // Keep the selection valid if the admin unchecks the current default locale
    if (
      defaultLocaleOptions.length &&
      !defaultLocaleOptions.some((o) => o.value === form.form.default_locale)
    ) {
      form.form.default_locale = defaultLocaleOptions[0].value
    }
  })
</script>

<PageLayout
  seoTitle={m['admin.nav.locales']()}
  title={m['admin.nav.locales']()}
  subtitle={m['admin.settings.subtitle']()}
>
  <Form id="locales" {...form} class="max-w-[480px]">
    <FormCheckboxGroup
      id="enabled_locales"
      label={m['admin.settings.locales.enabled.label']()}
      help={m['admin.settings.locales.enabled.hint']()}
      options={locales.allOptions}
      errors={form.errors}
      bind:value={form.form.enabled_locales}
    />

    <FormSelect
      id="default_locale"
      label={m['admin.settings.locales.default.label']()}
      bind:value={form.form.default_locale}
      errors={form.errors}
      options={defaultLocaleOptions}
    />
  </Form>
</PageLayout>
