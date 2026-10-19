<script lang="ts">
  import { provideLegalLinksContext } from '$lib/informational-pages.svelte'
  import { informationalLegalPageLinks } from './mock-data'

  let { Component, props = {} }: { Component: any; props?: any } = $props()

  provideLegalLinksContext(() => informationalLegalPageLinks)
</script>

<Component {...props} />
