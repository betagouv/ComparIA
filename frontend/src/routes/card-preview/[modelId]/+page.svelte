<!--
  Card preview route — used to generate social media visuals for model announcements.
  Renders a single ModelCard at 1080x1080 with a configurable background color.

  Query params:
    bg     — background hex color (default: #FFD500)
    locale — language code: da, en, fr, lt, sv (default: fr, handled by Paraglide middleware)

  Example: /card-preview/glm-5.1?bg=%234A6CF7&locale=en

  To generate a PNG, run: npx tsx scripts/generate-model-card.ts <modelId> [--bg <color>] [--locale <code>]
-->
<script lang="ts">
  import ModelCard from '$components/ModelCard.svelte'
  import { page } from '$app/state'
  import { getModelsContext } from '$lib/models'

  const { models } = getModelsContext()
  const model = $derived(models.find((m) => m.id === page.params.modelId))
  const bg = $derived(page.url.searchParams.get('bg') ?? '#FFD500')
</script>

<svelte:head>
  <style>
    /* Hide root layout extras */
    #tooltips {
      display: none;
    }
    html,
    body {
      min-height: auto !important;
      background: transparent !important;
    }
  </style>
</svelte:head>

{#if model}
  <div
    id="card-preview"
    class="flex items-center justify-center"
    style="background-color: {bg}; width: 1080px; height: 1080px;"
  >
    <div class="origin-center scale-[2.2]">
      <div
        class="w-[340px] [&>.fr-card]:min-h-[380px] [&>.fr-card]:border-[--border-default-grey]! [&>.fr-card]:shadow-lg"
      >
        <ModelCard {model} onModelSelected={() => {}} modalId="preview-modal" />
      </div>
    </div>
  </div>
{:else}
  <div class="flex items-center justify-center p-12 text-2xl text-red-600">
    Model "{page.params.modelId}" not found
  </div>
{/if}
