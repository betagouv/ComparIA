<script lang="ts">
  import { Toast } from '$components/dsfr'
  import { toasts } from '$lib/helpers/useToast.svelte'
  import { fade, fly } from 'svelte/transition'
</script>

<ul class="fixed right-0 bottom-0 z-[1751] m-0! max-w-full p-5!">
  {#each toasts.items as item (item.id)}
    <li class="list-none p-0! not-last:mb-3" in:fly out:fade>
      <Toast {...item} />
    </li>
  {/each}
</ul>
