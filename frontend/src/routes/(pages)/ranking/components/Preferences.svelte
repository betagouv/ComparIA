<script lang="ts">
  import Pending from '$components/Pending.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'
  import vegaEmbed from 'vega-embed'

  const graphs = [
    {
      id: 'trust',
      title: 'Intervalles de confiance sur le score du modèle',
      filename: 'elo_random_scores_confidence.json'
    },
    {
      id: 'meanwin',
      title: 'Taux de victoire moyen par rapport à tous les autres modèles',
      filename: 'elo_random_winrate_plot.json'
    },
    {
      id: 'winrate',
      title: 'Victoires du modèle A pour toutes les batailles contre B',
      filename: 'elo_random_winrate_heatmap.json'
    },
    {
      id: 'count',
      title: 'Nombre de batailles pour chaque combinaison de modèles',
      filename: 'elo_random_count_heatmap.json'
    }
  ]

  let graphLoading = $state(true)

  onMount(async () => {
    await Promise.all(
      graphs.map((graph) => {
        return graph.filename
          ? fetch(`/dataviz/${graph.filename}`).then((resp) => resp.json())
          : null
      })
    ).then((schemas) => {
      return Promise.all(
        schemas.map((schema, i) => {
          if (!schema) return
          return vegaEmbed(`#${graphs[i].id}`, schema, { mode: 'vega-lite' })
        })
      )
    })
    graphLoading = false
  })
</script>

<div id="ranking-preferences" class="fr-container">
  <h2 class="fr-h3 mb-10!">{m['ranking.graphs.title']()}</h2>

  <div class="grid gap-6 lg:grid-cols-2">
    {#each graphs as graph}
      <div class="cg-border bg-white px-8 py-10">
        <h2 class="fr-h6 mb-3!">{graph.title}</h2>
        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit</p>

        <div id={graph.id} class="graph p-0! w-full"></div>

        {#if graphLoading}<Pending />{/if}
      </div>
    {/each}
  </div>
</div>

<style>
  :global(svg) {
    width: 100%;
    height: auto;
  }
  :global(.graph details) {
    display: none;
  }
</style>
