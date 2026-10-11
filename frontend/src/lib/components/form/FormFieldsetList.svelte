<script module lang="ts">
  export type FormFieldsetListProps = {
    subProps: AnyFormItemProps
    // The admin form only holds the keys the user touched, so the list may
    // render before its own key exists.
  } & BaseFormFieldProps<'fieldset-list'>
</script>

<script lang="ts">
  import { Button } from '$components/dsfr'
  import AnyFormItem from '$components/form/AnyFormItem.svelte'
  import type { AnyFormItemProps, BaseFormFieldProps } from '$lib/utils/form'
  import { FormFieldset } from '.'

  let {
    value = $bindable(),
    disabled,
    subProps,
    ...props
  }: FormFieldsetListProps & { value?: any[] } = $props()

  const subIsFieldsetItem = $derived(subProps.component === 'fieldset-item')
  function onAdd() {
    value = [...(value ?? []), subIsFieldsetItem ? {} : '']
  }
  function onDelete(index: number) {
    value = (value ?? []).filter((_, i) => i !== index)
  }
</script>

<FormFieldset {...props} {disabled} component="fieldset">
  {#snippet formItem()}
    <div class="mx-2 w-full">
      {#each value ?? [] as _v, i (i)}
        <div class="fr-fieldset__element cg-border! p-4! gap-3 flex w-full!">
          <div class="w-full">
            <AnyFormItem
              {...subProps}
              disabled={disabled ?? subProps.disabled}
              id="{props.id}-{subIsFieldsetItem ? i : subProps.id}"
              label="{props.label} {i}"
              bind:value={value![i]}
              errors={props.errors}
            />
          </div>

          <Button
            text="delete"
            icon="delete-line"
            variant="tertiary-no-outline"
            size="sm"
            iconOnly
            {disabled}
            onclick={() => onDelete(i)}
            class="self-start!"
          />
        </div>
      {/each}
    </div>
    <Button text="add" icon="add-line" iconOnly {disabled} class="ms-2" onclick={onAdd} />
  {/snippet}
</FormFieldset>

<style lang="postcss">
</style>
