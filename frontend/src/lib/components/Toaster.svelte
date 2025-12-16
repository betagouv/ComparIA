<script lang="ts">
  import { Toast } from '$components/dsfr'
  import { toasts } from '$lib/helpers/useToast.svelte'
  import { fade, fly } from 'svelte/transition'
</script>

<ul class="right-0 bottom-0 m-0! p-5! fixed z-[1751] max-w-full">
  {#each toasts.items as item (item.id)}
    <li class="p-0! not-last:mb-3 list-none" in:fly out:fade>
      <Toast {...item} />
    </li>
  {/each}
</ul>
