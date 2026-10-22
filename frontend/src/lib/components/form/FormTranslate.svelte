<script module lang="ts">
  export type FormFieldsetItemProps = {
    subProps?: AnyFormItemProps
  } & Omit<BaseFormFieldProps<'translate'>, 'label'>
</script>

<script lang="ts">
  import { Segmented } from '$components/dsfr'
  import AnyFormItem from '$components/form/AnyFormItem.svelte'
  import { getAuthContext } from '$lib/authContext.svelte'
  import { getLocales } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import type { AnyFormItemProps, BaseFormFieldProps } from '$lib/utils/form'
  import type { Snippet } from 'svelte'

  const auth = getAuthContext()

  // FIXME handle error display, form.ts integration
  let {
    id,
    value = $bindable({}),
    locale = $bindable(auth.config.default_locale),
    subProps,
    isValid = (locale) => !!value[locale],
    subSnippet,
    ...props
  }: Omit<FormFieldsetItemProps, 'component'> & {
    value: Record<string, unknown>
    locale?: string
    isValid?: (locale: string) => boolean
    subSnippet?: Snippet<[locale: string, label: string]>
  } = $props()

  const locales = $derived(getLocales(auth.config.enabled_locales))
  const label = $derived(locales.find((l) => locale === l.code)!.long)
  const options = $derived(
    locales.map((locale) => ({
      value: locale.code,
      label: locale.long,
      icon: isValid(locale.code) ? 'i-ri-checkbox-fill' : 'i-ri-checkbox-blank-line'
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
