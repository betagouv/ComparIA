<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { ClassValue } from 'svelte/elements'

  let { onclick, class: classes }: { onclick: () => void; class?: ClassValue } = $props()
</script>

<button
  type="button"
  class={[
    'fr-link fr-icon-download-line fr-link--icon-right bg-transparent! bg-none! text-[14px]! no-underline!',
    classes
  ]}
  {onclick}
>
  {m['actions.downloadData']()}
</button>
