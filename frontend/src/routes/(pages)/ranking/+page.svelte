<script lang="ts">
  import { Tabs, Toggle, Tooltip } from '$components/dsfr'
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import { getModelsContext, getModelsWithDataContext } from '$lib/models'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'
  import { downloadTextFile, sortIfDefined } from '$lib/utils/data'
  import { Energy, Methodology, RankingTable } from './components'

  // Shared toggle state for style control (used in both ranking and energy tabs)
  let useStyleControl = $state(false)

  const tabs = (
    [
      { id: 'ranking', icon: 'trophy-line' },
      { id: 'energy', icon: 'flashlight-line' },
      // { id: 'preferences', icon: 'thumb-up-line' },
      { id: 'methodo' }
    ] as const
  ).map((tab) => ({
    ...tab,
    label: m[`ranking.${tab.id}.tabLabel`]()
  }))

  const { lastUpdateDate, models: modelsData } = getModelsWithDataContext()

  function onDownloadData(kind: 'ranking' | 'energy') {
    // Transform data based on style control toggle (match RankingTable logic)
    const exportData = useStyleControl
      ? getModelsContext()
          .models.filter((model) => {
            if (!model.data?.style_controlled) return false
            if (!model.prefs) return false
            return true
          })
          .map((model) => {
            const sc = model.data!.style_controlled!
            return {
              ...model,
              data: {
                ...model.data,
                elo: sc.elo,
                rank: sc.rank,
                score_p2_5: sc.score_p2_5,
                score_p97_5: sc.score_p97_5,
                rank_p2_5: sc.rank_p2_5,
                rank_p97_5: sc.rank_p97_5,
                trust_range: sc.trust_range
              }
            }
          })
      : modelsData

    const csvCols = [
      { key: 'rank' as const, label: 'Rank' },
      { key: 'id' as const, label: 'id', energy: true },
      { key: 'elo' as const, label: 'Bradley-Terry Score', energy: true },
      { key: 'score_p2_5' as const, label: 'BT p2.5' },
      { key: 'score_p97_5' as const, label: 'BT p97.5' },
      { key: 'trust_range' as const, label: 'Confidence interval' },
      { key: 'rank_p2_5' as const, label: 'Rank p2.5' },
      { key: 'rank_p97_5' as const, label: 'Rank p97.5' },
      { key: 'n_match' as const, label: 'Total votes' },
      { key: 'consumption_wh' as const, label: 'Consumption Wh (1000 tokens)', energy: true },
      { key: 'friendly_size' as const, label: 'Size', energy: true },
      { key: 'params' as const, label: 'Parameters (B)', energy: true },
      { key: 'arch' as const, label: 'Architecture', energy: true },
      { key: 'release_date' as const, label: 'Release' },
      { key: 'organisation' as const, label: 'Organisation', energy: true },
      { key: 'distribution' as const, label: 'License', energy: true }
    ]
    const cols = kind === 'ranking' ? csvCols : csvCols.filter((col) => col.energy)
    const data = [
      cols.map((col) => col.label).join(','),
      ...exportData
        .sort((a, b) => sortIfDefined(a.data, b.data, 'elo'))
        .map((m) => {
          return cols
            .map((col) => {
              if (
                col.key === 'elo' ||
                col.key === 'rank' ||
                col.key === 'n_match' ||
                col.key === 'rank_p2_5' ||
                col.key === 'rank_p97_5' ||
                col.key === 'score_p2_5' ||
                col.key === 'score_p97_5'
              )
                return m.data[col.key]
              if (col.key === 'params') return m.license === 'proprietary' ? 'N/A' : m.params
              if (col.key === 'trust_range')
                return `+${m.data.trust_range![0]}/-${m.data.trust_range![1]}`
              if (col.key === 'consumption_wh') {
                return m.license === 'proprietary' ? 'N/A' : m.consumption_wh
              }
              return m[col.key]
            })
            .join(',')
        })
    ].join('\n')

    const suffix = useStyleControl ? '-style_controlled' : ''
    downloadTextFile(data, `comparia_model-${kind}${suffix}-${lastUpdateDate}-license_Etalab_2_0`)
  }

  // function onDownloadPrefsData() {
  //   const csvCols = [
  //     { key: 'id' as const, label: 'id' },
  //     { key: 'positive_prefs_ratio' as const, label: 'positive ratio' },
  //     { key: 'total_prefs' as const, label: 'total prefs' },
  //     { key: 'total_positive_prefs' as const, label: 'total positive' },
  //     { key: 'total_negative_prefs' as const, label: 'total negative' },
  //     ...[...APIPositiveReactions, ...APINegativeReactions].map((reaction) => ({
  //       key: reaction,
  //       label: reaction.replaceAll('_', ' ')
  //     }))
  //   ]

  //   const data = [
  //     csvCols.map((col) => col.label).join(','),
  //     ...modelsData
  //       .sort((a, b) => sortIfDefined(a.prefs, b.prefs, 'positive_prefs_ratio'))
  //       .map((m) => {
  //         return csvCols
  //           .map((col) => {
  //             if (col.key === 'id') {
  //               return m[col.key]
  //             } else if (col.key === 'total_positive_prefs') {
  //               return APIPositiveReactions.reduce((acc, v) => acc + m.prefs[v], 0)
  //             } else if (col.key === 'total_negative_prefs') {
  //               return APINegativeReactions.reduce((acc, v) => acc + m.prefs[v], 0)
  //             } else {
  //               return m.prefs[col.key]
  //             }
  //           })
  //           .join(',')
  //       })
  //   ].join('\n')

  //   downloadTextFile(data, `comparia_model-preferences-${lastUpdateDate}-license_Etalab_2_0`)
  // }
</script>

<SeoHead title={m['seo.titles.ranking']()} />

<main class="bg-light-grey pt-12 pb-30">
  <div class="fr-container">
    <h1 class="fr-h3 mb-8!">{m['ranking.title']()}</h1>

    <Tabs {tabs} label={m['ranking.title']()} noBorders kind="nav">
      {#snippet headerRight()}
        <div class="style-control-toggle flex items-center gap-3 flex-nowrap">
          <Toggle
            id="style-control"
            bind:value={useStyleControl}
            label={m['ranking.styleControl.label']()}
            variant="primary"
            hideCheckLabel
          />
          <Tooltip id="style-control-tooltip" size="sm">
            {m['ranking.styleControl.tooltip']()}
          </Tooltip>
        </div>
      {/snippet}
      {#snippet tab({ id })}
        {#if id === 'ranking'}
          <p class="mb-8! text-dark-grey text-[14px]!">
            {@html sanitize(
              m['ranking.ranking.desc']({
                linkProps: externalLinkProps('https://www.peren.gouv.fr/')
              })
            )}
          </p>

          <RankingTable
            id="ranking-table"
            onDownloadData={() => onDownloadData('ranking')}
            {useStyleControl}
          />
        {:else if id === 'energy'}
          <Energy onDownloadData={() => onDownloadData('energy')} {useStyleControl} />
          <!-- {:else if id === 'preferences'}
          <Preferences onDownloadData={() => onDownloadPrefsData()} /> -->
        {:else if id === 'methodo'}
          <Methodology />
        {/if}
      {/snippet}
    </Tabs>
  </div>
</main>

<style lang="postcss">
  .style-control-toggle {
    :global(.fr-toggle__label) {
      font-weight: 700;
      font-size: 1rem;
      white-space: nowrap;
      padding-right: 3.5rem;
    }
  }
</style>
