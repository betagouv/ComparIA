<script lang="ts">
  import { Toast } from '$components/dsfr'
  import { toasts } from '$lib/helpers/useToast.svelte'
  import { fade, fly } from 'svelte/transition'
</script>

<ul class="top-0 m-0! p-5! fixed left-1/2 z-[1751] w-max max-w-full -translate-x-1/2">
  {#each toasts.items as item (item.id)}
    <li class="p-0! not-last:mb-3 list-none" in:fly out:fade>
      <Toast {...item} />
    </li>
  {/each}
</ul>
