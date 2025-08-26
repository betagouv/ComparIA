<script lang="ts">
  import { Toast } from '$components/dsfr'
  import { toasts } from '$lib/helpers/useToast.svelte'
  import { fade, fly } from 'svelte/transition'
</script>

<ul class="p-5! m-0! fixed bottom-0 right-0 z-[1751] max-w-full">
  {#each toasts.items as item (item.id)}
    <li class="not-last:mb-3 p-0! list-none" in:fly out:fade>
      <Toast {...item} />
    </li>
  {/each}
</ul>
