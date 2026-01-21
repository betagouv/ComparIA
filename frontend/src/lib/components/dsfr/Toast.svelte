<script lang="ts">
  import { Icon } from '$components/dsfr'
  import type { ToastItem } from '$lib/helpers/useToast.svelte'
  import { removeToast } from '$lib/helpers/useToast.svelte'
  import { onDestroy, onMount } from 'svelte'

  let { id, text, duration, variant = 'primary' }: ToastItem = $props()

  let timer = $state<number>()

  onMount(() => {
    timer = setTimeout(() => onClose(), duration)
  })

  onDestroy(() => {
    if (timer) clearTimeout(timer)
  })

  function onClose() {
    clearTimeout(timer)
    removeToast(id)
  }
</script>

<div
  class="cl-toast {variant === 'error'
    ? 'border-error'
    : 'border-primary'} text-dark-grey bg-white flex border-2"
>
  <div class="{variant === 'error' ? 'bg-error' : 'bg-primary'} p-2 flex flex-col justify-center">
    <Icon
      icon={variant === 'error' ? 'error-fill' : 'i-ri-checkbox-circle-line'}
      size="xs"
      class="text-white"
    />
  </div>
  <div class="px-2 py-1">{text}</div>
  <button onclick={onClose} class="p-2 ms-auto! self-start">
    <Icon icon="i-ri-close-line" block size="xs" />
  </button>
</div>

<style>
  .cl-toast {
    box-shadow: 0 1px 5px rgba(0, 0, 0, 0.1);
    width: 400px;
    max-width: 100%;
  }
</style>
