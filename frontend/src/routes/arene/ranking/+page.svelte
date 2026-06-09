<script lang="ts">
  import { Tabs, Toggle, Tooltip } from '$components/dsfr'
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import { applyStyleControl, getModelsWithDataContext } from '$lib/models'
  import { styleControl } from '$lib/styleControl.svelte'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'
  import { downloadTextFile, sortIfDefined } from '$lib/utils/data'
  import { Energy, Methodology, RankingTable } from './components'

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

  // Local mirror the DSFR Toggle binds to, pushed to the shared singleton that
  // every ranking view reads (RankingTable, EnergyGraph, the CSV export).
  let styleEnabled = $state(styleControl.enabled)
  $effect(() => {
    styleControl.enabled = styleEnabled
  })

  function onDownloadData(kind: 'ranking' | 'energy') {
    if (modelsData.length === 0) return

    // Export the view currently on screen (style-controlled or plain).
    const viewData = applyStyleControl(modelsData)

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
      { key: 'consumption' as const, label: 'Consumption mWh (1000 tokens)', energy: true },
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
      ...viewData
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
              if (col.key === 'consumption') {
                return m.license === 'proprietary' ? 'N/A' : m.consumption
              }
              return m[col.key]
            })
            .join(',')
        })
    ].join('\n')

    downloadTextFile(data, `comparia_model-${kind}-${lastUpdateDate}-license_Etalab_2_0`)
  }

  // function onDownloadPrefsData() {
  //   const csvCols = [
  //     { key: 'id' as const, label: 'id' },
  //     { key: 'positive_prefs_ratio' as const, label: 'positive ratio' },
  //     { key: 'total_prefs' as const, label: 'total prefs' },
  //     { key: 'total_positive_prefs' as const, label: 'total positive' },
  //     { key: 'total_negative_prefs' as const, label: 'total negative' },
  //     ...[...APIPositivePrefs, ...APINegativePrefs].map((pref) => ({
  //       key: pref,
  //       label: pref.replaceAll('_', ' ')
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
  //               return APIPositivePrefs.reduce((acc, v) => acc + m.prefs[v], 0)
  //             } else if (col.key === 'total_negative_prefs') {
  //               return APINegativePrefs.reduce((acc, v) => acc + m.prefs[v], 0)
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

<div class="px-4 md:px-6 pt-12 pb-30">
  <h1 class="fr-h3 mb-8!">{m['ranking.title']()}</h1>

  {#if lastUpdateDate}
    <div class="relative">
      <Tabs {tabs} noBorders kind="nav">
        {#snippet tab({ id })}
          {#if id === 'ranking'}
            <p class="mb-12! text-dark-grey text-[14px]!">
              {@html sanitize(
                m['ranking.ranking.desc']({
                  linkProps: externalLinkProps('https://www.peren.gouv.fr/')
                })
              )}
            </p>

            <RankingTable id="ranking-table" onDownloadData={() => onDownloadData('ranking')} />
          {:else if id === 'energy'}
            <Energy onDownloadData={() => onDownloadData('energy')} />
            <!-- {:else if id === 'preferences'}
          <Preferences onDownloadData={() => onDownloadPrefsData()} /> -->
          {:else if id === 'methodo'}
            <Methodology />
          {/if}
        {/snippet}
      </Tabs>

      <!-- Placed after the tabs in the DOM so it paints above the tab list and
           stays clickable; absolutely positioned over the tab row on md+. -->
      <div class="mb-4 gap-2 md:absolute md:top-0 md:right-0 md:mb-0 z-10 flex items-center">
        <Toggle
          id="style-control"
          bind:value={styleEnabled}
          label={m['ranking.styleControl.label']()}
          hideCheckLabel
          class="mb-0! pr-13! font-medium text-[14px]! whitespace-nowrap"
        />
        <Tooltip id="style-control-help" size="sm">
          {@html sanitize(m['ranking.styleControl.help']())}
        </Tooltip>
      </div>
    </div>
  {:else}
    <p>{m['ranking.no_data']()}</p>
  {/if}
</div>
