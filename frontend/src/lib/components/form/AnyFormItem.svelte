<script lang="ts">
  import * as components from '$components/form'
  import type { AnyFormItemProps } from '$lib/utils/form'

  let { value = $bindable(), ...props }: AnyFormItemProps = $props()
</script>

{#if props.component === 'input'}
  <components.FormInput {...props} bind:value />
{:else if props.component === 'select'}
  <components.FormSelect {...props} bind:value />
{:else if props.component === 'toggle'}
  <components.FormToggle {...props} bind:value />
{:else if props.component === 'checkbox-group'}
  <components.FormCheckboxGroup {...props} bind:value />
{:else if props.component === 'fieldset-item'}
  <components.FormFieldsetItem {...props} bind:value />
{:else if props.component === 'fieldset-list'}
  <components.FormFieldsetList {...props} bind:value />
{:else}
  ERROR: Cannot render component {JSON.stringify(props)}
{/if}
