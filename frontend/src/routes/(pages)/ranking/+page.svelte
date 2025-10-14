<script lang="ts">
  import { Tabs } from '$components/dsfr'
  import SeoHead from '$components/SEOHead.svelte'
  import { APINegativeReactions, APIPositiveReactions } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { getModelsContext } from '$lib/models'
  import { sanitize } from '$lib/utils/commons'
  import { downloadTextFile, sortIfDefined } from '$lib/utils/data'
  import { Energy, Methodology, Preferences, RankingTable } from './components'

  const tabs = (
    [
      { id: 'ranking', icon: 'trophy-line' },
      { id: 'energy', icon: 'flashlight-line', iconClass: 'text-primary' },
      { id: 'preferences', icon: 'thumb-up-line', iconClass: 'text-primary' },
      { id: 'methodo' }
    ] as const
  ).map((tab) => ({
    ...tab,
    label: m[`ranking.${tab.id}.tabLabel`]()
  }))

  const modelsData = getModelsContext().filter((m) => !!m.elo)

  function onDownloadData(kind: 'ranking' | 'energy') {
    const csvCols = [
      { key: 'rank' as const, label: 'rank' },
      { key: 'id' as const, label: 'id', energy: true },
      { key: 'elo' as const, label: 'elo', energy: true },
      { key: 'trust_range' as const, label: 'confidence interval' },
      { key: 'n_match' as const, label: 'total votes' },
      { key: 'consumption_wh' as const, label: 'consumption (wh)', energy: true },
      { key: 'friendly_size' as const, label: 'size', energy: true },
      { key: 'params' as const, label: 'parameters', energy: true },
      { key: 'release_date' as const, label: 'release' },
      { key: 'organisation' as const, label: 'organisation', energy: true },
      { key: 'distribution' as const, label: 'distribution', energy: true }
    ]
    const cols = kind === 'ranking' ? csvCols : csvCols.filter((col) => col.energy)
    const data = [
      cols.map((col) => col.label).join(','),
      ...modelsData
        .sort((a, b) => sortIfDefined(a, b, 'elo'))
        .map((m, i) => {
          return cols
            .map((col) => {
              if (col.key === 'rank') return i.toString()
              if (col.key === 'params') return m.license === 'proprietary' ? 'N/A' : m.params
              if (col.key === 'trust_range') return `+${m.trust_range![0]}/-${m.trust_range![1]}`
              return m[col.key]
            })
            .join(',')
        })
    ].join('\n')

    downloadTextFile(data, kind)
  }

  function onDownloadPrefsData() {
    const csvCols = [
      { key: 'id' as const, label: 'id' },
      { key: 'positive_prefs_ratio' as const, label: 'positive ratio' },
      { key: 'total_prefs' as const, label: 'total prefs' },
      { key: 'total_positive_prefs' as const, label: 'total positive' },
      { key: 'total_negative_prefs' as const, label: 'total negative' },
      { key: 'n_match' as const, label: 'total matches' },
      ...[...APIPositiveReactions, ...APINegativeReactions].map((reaction) => ({
        key: reaction,
        label: reaction.replaceAll('_', ' ')
      }))
    ]

    const data = [
      csvCols.map((col) => col.label).join(','),
      ...modelsData
        .filter((m) => !!m.prefs)
        .sort((a, b) => sortIfDefined(a, b, 'positive_prefs_ratio'))
        .map((m) => {
          return csvCols
            .map((col) => {
              if (col.key === 'id' || col.key === 'n_match') {
                return m[col.key]
              } else if (col.key === 'total_positive_prefs') {
                return APIPositiveReactions.reduce((acc, v) => acc + m.prefs![v], 0)
              } else if (col.key === 'total_negative_prefs') {
                return APINegativeReactions.reduce((acc, v) => acc + m.prefs![v], 0)
              } else {
                return m.prefs![col.key]
              }
            })
            .join(',')
        })
    ].join('\n')

    downloadTextFile(data, 'preferences')
  }
</script>

<SeoHead title={m['seo.titles.ranking']()} />

<main class="pb-30 bg-light-grey pt-12">
  <div class="fr-container">
    <h1 class="fr-h3 mb-8!">{m['ranking.title']()}</h1>

    <Tabs {tabs} noBorders kind="nav">
      {#snippet tab({ id })}
        {#if id === 'ranking'}
          <p class="text-[14px]! text-dark-grey mb-12!">
            {@html sanitize(m['ranking.ranking.desc']())}
          </p>

          <RankingTable
            id="ranking-table"
            data={modelsData}
            onDownloadData={() => onDownloadData('ranking')}
          />
        {:else if id === 'energy'}
          <Energy data={modelsData} onDownloadData={() => onDownloadData('energy')} />
        {:else if id === 'preferences'}
          <Preferences data={modelsData} onDownloadData={() => onDownloadPrefsData()} />
        {:else if id === 'methodo'}
          <Methodology data={modelsData} />
        {/if}
      {/snippet}
    </Tabs>
  </div>
</main>
