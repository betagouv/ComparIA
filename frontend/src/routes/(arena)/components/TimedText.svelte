<script lang="ts">
  import { TIME_SLOT, type ResetTime } from './resetTime'

  /** `reset` is needed only when `text` holds TIME_SLOT. */
  let { text, reset }: { text: string; reset?: ResetTime } = $props()

  const [head, after] = $derived(text.split(TIME_SLOT))
  // The word before the time stays on its line: "à 10 h 24", never "à" alone.
  const before = $derived(after === undefined ? head : head.replace(/ $/, ' '))
</script>

{before}{#if after !== undefined}<time datetime={reset?.datetime}>{reset?.clock?.time}</time
  >{after}{/if}
