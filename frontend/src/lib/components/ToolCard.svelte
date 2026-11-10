<script lang="ts">
  import { Icon } from '$components/dsfr'
  import type { ToolPublic } from '$lib/generated/backend'

  let { tool }: { tool: ToolPublic } = $props()
</script>

<div class="gap-2 flex">
  <div class="b-1 rounded-sm h-8 w-8 -ms-6 flex border-[--grey-925-125]">
    <Icon
      icon={tool.key === 'web_search' ? 'i-ri-global-line' : 'i-ri-tools-line'}
      class="text-primary m-auto"
      block
    />
  </div>

  <div class="text-sm! lh-tight!">
    <strong>{tool.label}</strong><br />
    {#if tool.description}
      <span class="text-grey text-[11px]">{tool.description}</span>
    {/if}
  </div>
</div>
