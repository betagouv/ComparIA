<script lang="ts">
  import { Icon } from '$components/dsfr'
  import type { HardwareTier } from '$lib/mockModelExtras'

  let { tier, gpuCount }: { tier: HardwareTier; gpuCount: number } = $props()

  // One escalating axis (increasing hardware). Colors go green → red because, for
  // an environmental section, a bigger machine genuinely means a bigger footprint.
  // `short` keeps the spectrum labels to one line; the full name is in the detail.
  const STEPS: { id: HardwareTier; icon: string; short: string; color: string }[] = [
    { id: 'smartphone', icon: 'i-ri-smartphone-line', short: 'Smartphone', color: '#00963a' },
    { id: 'laptop', icon: 'i-ri-computer-line', short: 'Ordinateur', color: '#7fb800' },
    { id: 'workstation', icon: 'i-ri-hard-drive-2-line', short: 'Station', color: '#f9a01b' },
    { id: 'server', icon: 'i-ri-server-line', short: 'Serveur', color: '#e30613' }
  ]

  const current = $derived(STEPS.find((s) => s.id === tier) ?? STEPS[0])

  const statement = $derived(
    {
      smartphone: 'Fonctionne sur un smartphone',
      laptop: 'Fonctionne sur un ordinateur portable',
      workstation: 'Nécessite une carte graphique',
      server: `Nécessite ${gpuCount} cartes graphiques`
    }[tier]
  )

  const detail = $derived(
    {
      smartphone: 'Aucune carte graphique nécessaire',
      laptop: 'Aucune carte graphique nécessaire',
      workstation: 'Station de travail puissante (1 GPU)',
      server: 'Serveur multi-GPU'
    }[tier]
  )
</script>

<div class="flex flex-1 flex-col items-center text-center">
  <!-- hero: fills the available space and stays vertically centered -->
  <div class="flex flex-1 flex-col items-center justify-center gap-1 py-2">
    <Icon icon={current.icon} block class="h-12! w-12!" style="color: {current.color}" />
    <p class="text-dark-grey mt-1 mb-0! text-sm! font-bold leading-tight text-balance">{statement}</p>
    <p class="text-grey mb-0! text-xs!">{detail}</p>
  </div>

  <!-- spectrum: equal-width columns (icons evenly spaced), chevrons on the icon row -->
  <div class="mt-3 flex w-full items-start justify-center">
    {#each STEPS as step, i (step.id)}
      {@const active = step.id === tier}
      <div class="flex w-[58px] flex-col items-center gap-1">
        <Icon
          icon={step.icon}
          block
          class={['h-5! w-5!', active ? '' : 'text-grey opacity-30']}
          style={active ? `color: ${step.color}` : ''}
        />
        <span
          class={[
            'text-center text-[10px]! leading-tight',
            active ? 'text-dark-grey font-medium' : 'text-grey opacity-40'
          ]}
        >
          {step.short}
        </span>
      </div>
      {#if i < STEPS.length - 1}
        <Icon icon="i-ri-arrow-right-s-line" block class="text-grey h-5! w-5! shrink-0 opacity-30" />
      {/if}
    {/each}
  </div>
</div>
