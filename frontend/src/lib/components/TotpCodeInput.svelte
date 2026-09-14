<script lang="ts">
  import { Input } from '$components/dsfr'
  import type { ClassValue } from 'svelte/elements'

  let {
    id,
    value = $bindable(''),
    label,
    help,
    error,
    disabled = false,
    groupClass
  }: {
    id: string
    value: string
    label: string
    help?: string
    error?: string
    disabled?: boolean
    groupClass?: ClassValue
  } = $props()
</script>

<!-- Six digits from an authenticator app: numeric keypad on phones, and the
     browser may offer the code it just saw. Anything but digits is dropped. -->
<Input
  {id}
  bind:value
  type="text"
  {label}
  {help}
  {error}
  {disabled}
  inputmode="numeric"
  maxlength={6}
  autocomplete="one-time-code"
  oninput={(e) => {
    value = e.currentTarget.value.replace(/\D/g, '').slice(0, 6)
  }}
  required
  {groupClass}
/>
