<script lang="ts">
  import { Toast } from '$components/dsfr'
  import { toasts } from '$lib/helpers/useToast.svelte'
  import { fade, fly } from 'svelte/transition'
</script>

<!-- The list is always in the DOM, empty most of the time: a live region has to
     exist before its content arrives or screen readers announce nothing, and
     toasts are inserted the moment they fire. -->
<div
  role="status"
  aria-live="polite"
  class="top-0 fixed left-1/2 z-[1751] w-max max-w-full -translate-x-1/2"
>
  <ul class="m-0! p-5!">
    {#each toasts.items as item (item.id)}
      <li class="p-0! not-last:mb-3 list-none" in:fly out:fade>
        <Toast {...item} />
      </li>
    {/each}
  </ul>
</div>
