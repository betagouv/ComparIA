<script module lang="ts">
  export type FormFieldsetItemProps = {
    subProps?: AnyFormItemProps
  } & Omit<BaseFormFieldProps<'translate'>, 'label'>
</script>

<script lang="ts">
  import { Segmented } from '$components/dsfr'
  import AnyFormItem from '$components/form/AnyFormItem.svelte'
  import { getLocalesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import type { Locale } from '$lib/i18n/runtime'
  import type { AnyFormItemProps, BaseFormFieldProps } from '$lib/utils/form'
  import type { Snippet } from 'svelte'

  const locales = getLocalesContext()

  // FIXME handle error display, form.ts integration
  let {
    id,
    value = $bindable({}),
    locale = $bindable(locales.default),
    subProps,
    isValid = (locale) => !!value[locale],
    subSnippet,
    ...props
  }: Omit<FormFieldsetItemProps, 'component'> & {
    value: Record<string, unknown>
    locale?: Locale
    isValid?: (locale: Locale) => boolean
    subSnippet?: Snippet<[locale: Locale, label: string]>
  } = $props()

  const label = $derived(locales.getLabel(locale))
  const options = $derived(
    locales.enabledOptions.map((opt) => ({
      ...opt,
      icon: isValid(opt.value) ? 'i-ri-checkbox-fill' : 'i-ri-checkbox-blank-line'
    }))
  )
</script>

<div class="mb-4">
  <Segmented
    {id}
    legend={m['actions.selectLanguage']()}
    {options}
    bind:value={locale}
    hideLegend
    size="sm"
    class="mb-3!"
  />

  {#if subProps}
    <AnyFormItem
      {...subProps}
      id="{id}-{subProps.id}"
      bind:value={value[locale]}
      errors={props.errors}
    />
  {:else}
    {@render subSnippet?.(locale, label)}
  {/if}
</div>
