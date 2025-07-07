<script lang="ts">
  import TextBox from '$lib/components/FrInputTextbox.svelte'
  import type { LoadingStatus } from '@gradio/statustracker'
  // import { StatusTracker } from '@gradio/statustracker'

  export let label = 'Textbox'
  export let elem_id = ''
  export let elem_classes: string[] = []
  export let visible = true
  export let value = ''
  export let lines: number
  export let placeholder = ''
  export let show_label: boolean
  export let max_lines: number
  export let type: 'text' | 'password' | 'email' = 'text'
  // export let scale: number | null = null;
  // export let min_width: number | undefined = undefined;
  export let show_copy_button = false
  export let loading_status: LoadingStatus | undefined = undefined
  export let value_is_output = false
  export let rtl = false
  export let text_align: 'left' | 'right' | undefined = undefined
  export let autofocus = false
  export let autoscroll = true
  export let disabled: boolean = false
  export let onSelect: (selection: { value: string; indexes: [number, number] }) => void = () => {}
  export let onSubmit: (value: string) => void
</script>

<!-- FIXME still needed? -->
<!-- {#if loading_status}
  <StatusTracker
    autoscroll={gradio.autoscroll}
    i18n={gradio.i18n}
    {...loading_status}
    on:clear_status={() => gradio.dispatch('clear_status', loading_status)}
  />
{/if} -->

<TextBox
  bind:value
  bind:value_is_output
  {elem_id}
  {elem_classes}
  {visible}
  {label}
  {show_label}
  {lines}
  {type}
  {rtl}
  {text_align}
  max_lines={!max_lines ? lines + 1 : max_lines}
  {placeholder}
  {show_copy_button}
  {autofocus}
  {autoscroll}
  {disabled}
  {onSelect}
  {onSubmit}
/>
