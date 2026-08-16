<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Button, Icon, Link, Segmented, Tabs, Toggle, Tooltip } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { getAuthContext, openSignInModal } from '$lib/auth.svelte'
  import { getVotesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import {
    applyStyleControl,
    getModelsContext,
    getModelsWithDataContext,
    joinPersonalRanking,
    rankClassSpans
  } from '$lib/models'
  import { styleControl } from '$lib/styleControl.svelte'
  import { sanitize } from '$lib/utils/commons'
  import { downloadTextFile, sortIfDefined } from '$lib/utils/data'
  import { Energy, Methodology, PersonalTable, RankingTable } from './components'
  import type { RankingView } from './+page'

  let { data } = $props()

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

  const viewIcons = { general: '🌐', personal: '🙋' }
  const viewOptions = (['general', 'personal'] as const).map((value) => ({
    value,
    label: m[`ranking.views.${value}`](),
    icon: viewIcons[value]
  }))

  const { lastUpdateDate, commons, models: modelsData } = getModelsWithDataContext()
  // The full list, not only the ranked models: a model the user voted on can
  // have dropped out of the general ranking and still needs its size and
  // architecture.
  const { models: allModels } = getModelsContext()
  const votesData = getVotesContext()
  const auth = getAuthContext()

  let currentTabId = $state<(typeof tabs)[number]['id']>(tabs[0].id)
  // The switcher writes to it, the address bar overrules it, so back and
  // forward move between the two views.
  let view: RankingView = $derived(data.view)

  function onViewChange() {
    goto(
      view === 'personal' ? `${resolve('/ranking')}?view=personal` : resolve('/ranking'),
      {
        noScroll: true,
        keepFocus: true
      }
    )
  }

  // Local mirror the DSFR Toggle binds to, pushed to the shared singleton that
  // every ranking view reads (RankingTable, EnergyGraph, the CSV export).
  let styleEnabled = $state(styleControl.enabled)
  $effect(() => {
    styleControl.enabled = styleEnabled
  })

  const rankingRows = $derived(applyStyleControl(modelsData))
  // Turning style control off is a different fit of the same votes, with its
  // own classes, so the spans handed to the table follow whichever rows it
  // is about to render rather than the ones the layout fetched at load time.
  const rankingCommons = $derived({
    ...commons,
    rankClasses: rankClassSpans(rankingRows.map((m) => m.data))
  })

  // Personal rows arrive with an identifier and nothing else, so the model list
  // supplies the metadata and the rows of the general view supply the ranks the
  // user sees on the other side of the switcher.
  const personalRows = $derived(
    joinPersonalRanking(
      data.personal?.rows ?? [],
      allModels,
      Object.fromEntries(rankingRows.map((model) => [model.id, model.data.rank]))
    )
  )
  // Style control is a property of the global fit, with no personal
  // counterpart.
  const showStyleControl = $derived(!(currentTabId === 'ranking' && view === 'personal'))

  // The sign-in form mutates auth.user in place, client-side, with no
  // navigation and no reload. The personal ranking still needs fetching, so
  // catch the transition here rather than teaching the shared sign-in modal
  // about this one page.
  const personalPending = $derived(
    view === 'personal' && !!auth.user && !data.personal && !data.personalFailed
  )
  $effect(() => {
    if (personalPending) invalidateAll()
  })

  function onDownloadData(kind: 'ranking' | 'energy') {
    if (modelsData.length === 0) return

    // Export the view currently on screen (style-controlled or plain).
    const viewData = applyStyleControl(modelsData)

    const csvCols = [
      { key: 'rankClass' as const, label: 'Class' },
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
      { key: 'size_class' as const, label: 'Size', energy: true },
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
                col.key === 'rankClass' ||
                col.key === 'n_match' ||
                col.key === 'rank_p2_5' ||
                col.key === 'rank_p97_5' ||
                col.key === 'score_p2_5' ||
                col.key === 'score_p97_5'
              )
                return m.data[col.key]
              if (col.key === 'params') return m.license.kind === 'proprietary' ? 'N/A' : m.params
              if (col.key === 'trust_range')
                return `+${m.data.trust_range![0]}/-${m.data.trust_range![1]}`
              if (col.key === 'consumption') {
                return m.license.kind === 'proprietary' ? 'N/A' : m.consumption
              }
              if (col.key === 'organisation') return m.lab.name
              if (col.key === 'distribution') return m.license.kind
              if (col.key === 'id') return m.human_id
              return m[col.key]
            })
            .join(',')
        })
    ].join('\n')

    downloadTextFile(data, `comparia_model-${kind}-${lastUpdateDate}-license_Etalab_2_0`)
  }

  // A user's own votes, live rather than snapshotted, so the filename is
  // dated today rather than tied to the general ranking's last update.
  function onDownloadPersonalData() {
    if (personalRows.length === 0) return

    const csvCols = [
      { key: 'rank' as const, label: 'Rank' },
      { key: 'name' as const, label: 'Model' },
      { key: 'score' as const, label: 'Score' },
      { key: 'battles' as const, label: 'Battles' },
      { key: 'record' as const, label: 'Record (W-L-T)' },
      { key: 'general_rank' as const, label: 'General rank' },
      { key: 'size' as const, label: 'Size' },
      { key: 'arch' as const, label: 'Architecture' }
    ]
    const csvData = [
      csvCols.map((col) => col.label).join(','),
      ...personalRows.map((row) =>
        csvCols
          .map((col) => {
            switch (col.key) {
              case 'rank':
                return row.rank
              case 'name':
                return row.model?.human_id ?? row.name
              case 'score':
                return row.score
              case 'battles':
                return row.battles
              case 'record':
                return `${row.wins}-${row.losses}-${row.ties}`
              case 'general_rank':
                return row.generalRank ?? ''
              case 'size':
                return row.model?.size_class ?? 'N/A'
              case 'arch':
                return row.model?.arch ?? 'N/A'
            }
          })
          .join(',')
      )
    ].join('\n')

    downloadTextFile(csvData, `comparia_personal-ranking-${new Date().toLocaleDateString()}`)
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
  //               return m.human_id
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

<PageLayout
  seoTitle={m['seo.titles.ranking']()}
  title={m['ranking.title']()}
  bubble={m['seo.titles.ranking']()}
>
  {#if lastUpdateDate}
    <div class="relative">
      {#if showStyleControl}
        <div class="mb-4 gap-2 md:absolute md:top-4 md:right-0 md:mb-0 z-10 flex items-center">
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
      {/if}

      <Tabs {tabs} label={m['seo.titles.ranking']()} noBorders kind="nav" bind:currentTabId>
        {#snippet tab({ id })}
          {#if id === 'ranking'}
            <Segmented
              id="ranking-view"
              legend={m['ranking.views.legend']()}
              hideLegend
              size="sm"
              options={viewOptions}
              bind:value={view}
              onchange={onViewChange}
              class="mb-6!"
            />

            {#if view === 'general'}
              <p class="mb-8! text-dark-grey text-[14px]!">
                {@html sanitize(m['ranking.ranking.desc']())}
              </p>

              <RankingTable
                id="ranking-table"
                models={rankingRows}
                commons={rankingCommons}
                {lastUpdateDate}
                totalVotes={votesData.count}
                onDownloadData={() => onDownloadData('ranking')}
              />
            {:else if !auth.user}
              <!-- Real ranking data, blurred: the pitch for signing in is what
                   the feature looks like, not a mock-up of it. -->
              <div class="rounded-xl relative h-[34rem] overflow-hidden">
                <div inert aria-hidden="true" class="blur-sm pointer-events-none select-none">
                  <RankingTable
                    id="ranking-table-preview"
                    models={rankingRows}
                    commons={rankingCommons}
                    {lastUpdateDate}
                    totalVotes={votesData.count}
                    onDownloadData={() => {}}
                  />
                </div>
                <div class="inset-0 absolute flex items-center justify-center">
                  <section
                    aria-labelledby="personal-signin-title"
                    class="cg-border bg-white shadow-lg mx-4 max-w-md rounded-xl px-6 py-8 text-center"
                  >
                    <span
                      aria-hidden="true"
                      class="bg-light-primary mb-4 size-14 mx-auto flex items-center justify-center rounded-full"
                    >
                      <Icon icon="lock-line" size="lg" class="text-primary" />
                    </span>
                    <h2 id="personal-signin-title" class="fr-h5 mb-2!">
                      {m['ranking.personal.title']()}
                    </h2>
                    <p class="mb-4! text-grey">{m['ranking.personal.signedOut']()}</p>
                    <Button text={m['auth.discussions.signIn']()} onclick={openSignInModal} />
                  </section>
                </div>
              </div>
            {:else if personalPending}
              <!-- Signing in mutates auth.user straight away, but the ranking
                   only arrives once the reload below finishes. Without this the
                   old signed-out panel stays on screen in between, telling
                   someone who just signed in to sign in. -->
              {@render emptyCard(
                'personal-loading-title',
                m['ranking.personal.title'](),
                m['ranking.personal.loading']()
              )}
            {:else if personalRows.length > 0}
              <PersonalTable
                id="personal-ranking-table"
                rows={personalRows}
                commons={rankingCommons}
                votesCount={data.personal!.votes_count}
                onDownloadData={onDownloadPersonalData}
              />
            {:else if data.personalFailed}
              {@render emptyCard(
                'personal-empty-title',
                m['ranking.personal.title'](),
                m['ranking.no_data']()
              )}
            {:else}
              {@render emptyCard(
                'personal-empty-title',
                m['ranking.personal.title'](),
                m['ranking.personal.noVotes'](),
                { href: resolve('/'), text: m['header.chatbot.newDiscussion']() }
              )}
            {/if}
          {:else if id === 'energy'}
            <Energy onDownloadData={() => onDownloadData('energy')} />
            <!-- {:else if id === 'preferences'}
          <Preferences onDownloadData={() => onDownloadPrefsData()} /> -->
          {:else if id === 'methodo'}
            <Methodology />
          {/if}
        {/snippet}
      </Tabs>
    </div>
  {:else}
    <div class="mt-8">
      {@render emptyCard('ranking-empty-title', m['seo.titles.ranking'](), m['ranking.no_data']())}
    </div>
  {/if}
</PageLayout>

{#snippet emptyCard(
  titleId: string,
  title: string,
  body: string,
  cta?: { href: string; text: string }
)}
  <section
    aria-labelledby={titleId}
    class="cg-border bg-very-light-grey max-w-2xl rounded-xl px-6 py-12 mx-auto text-center"
  >
    <span
      aria-hidden="true"
      class="bg-light-primary mb-5 size-16 mx-auto flex items-center justify-center rounded-full"
    >
      <Icon icon="trophy-line" size="lg" class="text-primary" />
    </span>
    <h2 id={titleId} class="fr-h4 mb-3!">{title}</h2>
    <p class={[cta ? 'mb-5!' : 'mb-0!', 'text-grey']}>{body}</p>
    {#if cta}
      <Link button href={cta.href} text={cta.text} />
    {/if}
  </section>
{/snippet}
