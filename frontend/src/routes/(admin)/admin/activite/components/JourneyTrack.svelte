<script lang="ts">
  import { STAGES, label, type Stage } from '../filters'

  let { stage }: { stage: Stage } = $props()

  const reached = $derived(STAGES.indexOf(stage))
</script>

<!-- The overview funnel's steps, for one conversation: the bars it got
     through are filled. -->
<span class="gap-2 flex items-center whitespace-nowrap">
  <span class="gap-0.5 flex" aria-hidden="true">
    {#each STAGES as step, index (step)}
      <span
        class={[
          'h-2 w-4 first:rounded-s-full last:rounded-e-full',
          index <= reached ? 'bg-[--blue-france-main-525]' : 'bg-[--background-contrast-grey]'
        ]}
      ></span>
    {/each}
  </span>
  <span class="fr-text--xs mb-0! text-[--text-default-grey]">{label('stages', stage)}</span>
</span>
