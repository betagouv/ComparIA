<script lang="ts">
  import { TIME_SLOT, type ResetTime } from './resetTime'

  let { text, reset }: { text: string; reset: ResetTime } = $props()

  const [before, after] = $derived(text.split(TIME_SLOT))
</script>

{before}{#if after !== undefined}<time datetime={reset.datetime}>{reset.clock?.time}</time
  >{after}{/if}
