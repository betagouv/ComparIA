<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { SideVerdict } from '../filters'

  let { verdict }: { verdict: SideVerdict } = $props()

  const marks = {
    preferred: { icon: 'i-ri-thumb-up-fill', tone: 'text-[--green-emeraude-sun-425-moon-753]' },
    rejected: { icon: 'i-ri-thumb-down-fill', tone: 'text-[--warning-425-625]' },
    mixed: { icon: 'i-ri-contrast-2-line', tone: 'text-[--text-mention-grey]' }
  }
</script>

{#if verdict}
  <span
    class={[marks[verdict].icon, marks[verdict].tone, 'shrink-0']}
    role="img"
    aria-label={m[`admin.activity.verdicts.${verdict}`]()}
    title={m[`admin.activity.verdicts.${verdict}`]()}
  ></span>
{/if}
