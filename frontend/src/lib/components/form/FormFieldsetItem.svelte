<script module lang="ts">
  export type FormFieldsetItemProps = {
    subProps: AnyFormItemProps[]
  } & BaseFormFieldProps<'fieldset-item', any>
</script>

<script lang="ts">
  import AnyFormItem from '$components/form/AnyFormItem.svelte'
  import type { AnyFormItemProps, BaseFormFieldProps } from '$lib/utils/form'
  import { FormFieldset } from '.'

  let { value = $bindable(), subProps, ...props }: FormFieldsetItemProps = $props()
</script>

<FormFieldset {...props} component="fieldset">
  {#snippet formItem()}
    {#each subProps as sub, i (i)}
      <div class="fr-fieldset__element">
        <AnyFormItem
          {...sub}
          id="{props.id}-{sub.id}"
          bind:value={value[sub.id]}
          errors={props.errors}
        />
      </div>
    {/each}
  {/snippet}
</FormFieldset>

<style lang="postcss">
</style>
