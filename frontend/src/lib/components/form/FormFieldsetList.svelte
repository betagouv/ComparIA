<script module lang="ts">
  export type FormFieldsetListProps = {
    subProps: AnyFormItemProps
  } & BaseFormFieldProps<'fieldset-list', any[]>
</script>

<script lang="ts">
  import Button from '$components/dsfr/Button.svelte'
  import AnyFormItem from '$components/form/AnyFormItem.svelte'
  import type { AnyFormItemProps, BaseFormFieldProps } from '$lib/utils/form'
  import { FormFieldset } from '.'

  let { value = $bindable([]), disabled, subProps, ...props }: FormFieldsetListProps = $props()

  const subIsFieldsetItem = $derived(subProps.component === 'fieldset-item')
  function onAdd() {
    value = [...value, subIsFieldsetItem ? {} : '']
  }
  function onDelete(index: number) {
    value = value.filter((_, i) => i !== index)
  }
</script>

<FormFieldset {...props} {disabled} component="fieldset">
  {#snippet formItem()}
    <div class="w-full">
      {#each value as _v, i (i)}
        <div class="fr-fieldset__element gap-3 flex w-full!">
          <div class="w-full">
            <AnyFormItem
              {...subProps}
              disabled={disabled ?? subProps.disabled}
              id="{props.id}-{subIsFieldsetItem ? i : subProps.id}"
              label="{props.label} {i}"
              bind:value={value[i]}
              errors={props.errors}
            />
          </div>

          <Button
            text="delete"
            icon="delete-line"
            iconOnly
            type="button"
            {disabled}
            onclick={() => onDelete(i)}
            class={subIsFieldsetItem ? 'self-center!' : 'self-end!'}
          />
        </div>
      {/each}
    </div>
    <Button text="add" icon="add-line" iconOnly type="button" {disabled} onclick={onAdd} />
  {/snippet}
</FormFieldset>

<style lang="postcss">
</style>
