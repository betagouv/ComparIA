<script lang="ts">
  import { Icon } from '$components/dsfr'

  let { icons, max = 3, count }: { icons: string[]; max?: number; count?: number } = $props()

  const displayed = $derived(icons.slice(0, max))

  function hideBrokenImage(event: Event) {
    const image = event.currentTarget
    if (image instanceof HTMLImageElement) image.hidden = true
  }
</script>

<div class="flex">
  {#each displayed as icon, i (i)}
    <div class="bg-white not-first:-ms-1 overflow-hidden rounded-full">
      {#if icon.startsWith('i-ri')}
        <Icon {icon} size="xs" block class="text-primary" />
      {:else}
        <img
          src={icon}
          alt=""
          aria-hidden="true"
          loading="lazy"
          onerror={hideBrokenImage}
          class="h-[16px] w-[16px] shrink-0"
        />
      {/if}
    </div>
  {/each}
  <span class="ms-1 text-xs text-[--grey-625-425]">{count ?? icons.length}</span>
</div>
