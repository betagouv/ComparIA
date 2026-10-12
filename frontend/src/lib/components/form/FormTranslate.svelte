<script module lang="ts">
  export type FormFieldsetItemProps = {
    subProps: AnyFormItemProps
  } & Omit<BaseFormFieldProps<'translate'>, 'label'>
</script>

<script lang="ts">
  import { Segmented } from '$components/dsfr'
  import AnyFormItem from '$components/form/AnyFormItem.svelte'
  import { getAuthContext } from '$lib/authContext.svelte'
  import { getLocales } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import type { AnyFormItemProps, BaseFormFieldProps } from '$lib/utils/form'

  // FIXME handle error display, form.ts integration
  let {
    id,
    value = $bindable({}),
    subProps,
    ...props
  }: Omit<FormFieldsetItemProps, 'component'> & { value: Record<string, string> } = $props()

  const auth = getAuthContext()
  const locales = $derived(getLocales(auth.config.enabled_locales))
  const options = $derived(
    locales.map((locale) => ({
      value: locale.code,
      label: locale.long,
      icon: value[locale.code] ? 'i-ri-checkbox-fill' : 'i-ri-checkbox-blank-line'
    }))
  )
  let locale = $derived(auth.config.default_locale)
</script>

<div>
  <Segmented
    {id}
    legend={m['actions.selectLanguage']()}
    {options}
    bind:value={locale}
    hideLegend
    size="sm"
    class="mb-3!"
  />

  <AnyFormItem
    {...subProps}
    id="{id}-{subProps.id}"
    bind:value={value[locale]}
    errors={props.errors}
  />
</div>
