<script lang="ts">
  import { api } from '$lib/fastapi-client'
  import { onMount } from 'svelte'
  import Header from '$components/header/Header.svelte'
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'

  type ToolRanking = {
    tool_id: string
    elo: number
    score_p2_5: number
    score_p97_5: number
    n_match: number
    win_rate: number
    provisional: boolean
  }

  let tools = $state<ToolRanking[]>([])
  let loading = $state(true)
  let error = $state<string | null>(null)

  onMount(async () => {
    try {
      const data = await api.request<{ data_timestamp: number | null; tools: ToolRanking[] }>('/tool-arena/leaderboard')
      tools = [...data.tools].sort((a, b) => b.elo - a.elo)
    } catch (err) {
      error = (err as Error).message || 'Failed to load leaderboard'
    } finally {
      loading = false
    }
  })
</script>

<SeoHead title={m['seo.titles.tool-arena']()} />

<Header hideDiscussBtn hideVoteGauge small />

<main class="bg-very-light-grey min-h-screen">
  <div class="fr-container py-10 md:py-16">
    <div class="mb-8 flex items-center justify-between">
      <h1 class="fr-h3 mb-0!">Tool Arena Leaderboard</h1>
      <a href="/tool-arena" class="fr-link fr-text--sm">
        &larr; Back to Tool Arena
      </a>
    </div>

    {#if loading}
      <div class="text-center py-16">
        <p class="fr-text--sm text-grey animate-pulse">Loading rankings...</p>
      </div>

    {:else if error}
      <div class="cg-border rounded-lg bg-white p-6 text-center">
        <p class="fr-text--sm text-red-600 mb-0!">{error}</p>
      </div>

    {:else if tools.length === 0}
      <div class="cg-border rounded-lg bg-white p-8 text-center">
        <p class="fr-text--sm text-grey mb-0!">
          No rankings available yet. Rankings are computed after votes are cast.
        </p>
      </div>

    {:else}
      <div class="bg-white rounded-lg overflow-x-auto cg-border">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-grey-200">
              <th class="text-left px-4 py-3 font-semibold text-dark-grey">Rank</th>
              <th class="text-left px-4 py-3 font-semibold text-dark-grey">Tool Name</th>
              <th class="text-right px-4 py-3 font-semibold text-dark-grey">ELO Score</th>
              <th class="text-right px-4 py-3 font-semibold text-dark-grey hidden md:table-cell">Confidence Interval</th>
              <th class="text-right px-4 py-3 font-semibold text-dark-grey">Matches</th>
              <th class="text-right px-4 py-3 font-semibold text-dark-grey hidden sm:table-cell">Win Rate</th>
            </tr>
          </thead>
          <tbody>
            {#each tools as tool, i}
              <tr class="border-b border-grey-100 last:border-0 hover:bg-very-light-grey transition-colors">
                <td class="px-4 py-3 font-semibold text-grey">{i + 1}</td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-medium">{tool.tool_id}</span>
                    {#if tool.provisional}
                      <span
                        class="fr-text--xs px-1.5 py-0.5 rounded"
                        style="background-color: #f5f5fe; color: #6b7280; border: 1px solid #e5e7eb;"
                      >
                        Provisional
                      </span>
                    {/if}
                  </div>
                </td>
                <td class="px-4 py-3 text-right font-mono">
                  {tool.elo.toFixed(1)}
                </td>
                <td class="px-4 py-3 text-right text-grey hidden md:table-cell font-mono fr-text--sm">
                  {tool.score_p2_5.toFixed(1)} – {tool.score_p97_5.toFixed(1)}
                </td>
                <td class="px-4 py-3 text-right text-grey">{tool.n_match}</td>
                <td class="px-4 py-3 text-right text-grey hidden sm:table-cell">
                  {(tool.win_rate * 100).toFixed(1)}%
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="fr-text--xs text-grey mt-3">
        ELO scores computed using the Bradley-Terry model with bootstrap confidence intervals (p2.5 – p97.5).
        Tools marked "Provisional" have fewer than 50 matches.
      </p>
    {/if}
  </div>
</main>
