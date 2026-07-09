<script lang="ts">
  import { page } from '$app/state'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()

  const llm = $derived(data.llms.find((llm) => llm.id === page.params.id))
</script>

<div>
  <pre class="text-xs">{JSON.stringify(llm, null, 2)}</pre>
</div>
