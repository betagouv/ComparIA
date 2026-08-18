<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import {
    getModelsWithDataContext,
    getStyleCoefficients,
    type BotModelWithData
  } from '$lib/models'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'
  import { downloadTextFile, sortIfDefined } from '$lib/utils/data'
  import { extent } from 'd3'
  import { WinHistogram } from '.'

  const { lastUpdateDate, models: data } = getModelsWithDataContext()

  // Live style-control coefficients, in the documented feature order. A positive
  // value means that presentation axis is associated with a higher win
  // probability once model strength is accounted for, i.e. how much raw votes
  // reward it; Style Control removes exactly this from the ranking.
  const STYLE_FEATURE_KEYS = ['length', 'md_headers', 'md_bold', 'md_lists'] as const
  const styleCoefficients = getStyleCoefficients()
  const styleRows = STYLE_FEATURE_KEYS.filter((key) => key in styleCoefficients).map((key) => ({
    key,
    label: m[`ranking.methodo.style.features.${key}`](),
    value: styleCoefficients[key]
  }))

  type WinKey = 'mean_win_prob' | 'win_rate'

  function formatModelData(data: BotModelWithData[], key: WinKey) {
    return data
      .filter((m) => !!m.data[key])
      .slice(0, 10)
      .sort((a, b) => b.data[key]! - a.data[key]!)
      .map((m) => ({
        x: m.id,
        y: m.data[key]!
      }))
  }

  const modelsData = $derived({
    win_rate: formatModelData(data, 'win_rate'),
    mean_win_prob: formatModelData(data, 'mean_win_prob')
  })

  const minMaxY = $derived.by(() => {
    const minMax = extent(Object.values(modelsData).flatMap((l) => l.map((l) => l.y)))
    // Reduce a bit the min so that the last bar have at least an height
    return [minMax[0]! - 0.02, minMax[1]!] as [number, number]
  })

  function onDownloadData() {
    const csvCols = [
      { key: 'id' as const, label: 'id' },
      { key: 'mean_win_prob' as const, label: 'mean win prob' },
      { key: 'win_rate' as const, label: 'classic winrate' }
    ]
    const csvData = [
      csvCols.map((col) => col.label).join(','),
      ...data
        .sort((a, b) => sortIfDefined(a, b, 'mean_win_prob'))
        .map((m) =>
          csvCols.map((col) => (col.key == 'id' ? m[col.key] : m.data[col.key])).join(',')
        )
    ].join('\n')

    downloadTextFile(csvData, `comparia_model-winrate-${lastUpdateDate}-license_Etalab_2_0`)
  }
</script>

<div id="ranking-methodo">
  <h2 class="fr-h6 mb-4! text-primary!">{m['ranking.methodo.title']()}</h2>
  <p class="mb-4! text-dark-grey text-[14px]!">{m['ranking.methodo.desc.1']()}</p>
  <p class="text-dark-grey text-[14px]!">
    {@html sanitize(
      m['ranking.methodo.desc.2']({
        notebookLinkProps: externalLinkProps({
          href: 'https://colab.research.google.com/drive/1j5AfStT3h-IK8V6FSJY9CLAYr_1SvYw7#scrollTo=LgXO1k5Tp0pq',
          class: 'text-primary!'
        }),
        perenLinkProps: externalLinkProps('https://www.peren.gouv.fr/')
      })
    )}
  </p>

  <section class="mt-10">
    <h3 class="fr-h6 mb-5!">{m['ranking.methodo.methods.title']()}</h3>

    <div class="gap-6 lg:grid-cols-2 grid">
      {#each [{ id: 'winrate', k: 'cons' }, { id: 'elo', k: 'pros' }] as const as card (card.id)}
        <div
          class={[
            'cg-border bg-white p-7 pb-8',
            { 'border-2! border-[--border-plain-success]!': card.k === 'pros' }
          ]}
        >
          <div class="flex h-full flex-col">
            <div class="xl:basis-[172px]">
              <h4 class="text-lg!">{m[`ranking.methodo.methods.${card.id}.title`]()}</h4>
              <p class="font-[14px]">
                {@html sanitize(m[`ranking.methodo.methods.${card.id}.def`]())}
              </p>
            </div>

            <h4 class="mb-5! text-lg!">{m[`ranking.methodo.methods.${card.k}`]()}</h4>
            <ul class="m-0! p-0! list-none!">
              {#each ['1', '2', '3'] as const as i (i)}
                <li class="p-0! not-last:mb-5 flex">
                  <Icon
                    icon={card.k === 'pros'
                      ? 'i-ri-checkbox-circle-line'
                      : 'i-ri-close-circle-fill'}
                    block
                    class={['me-1', card.k === 'pros' ? 'text-success' : 'text-error']}
                  />
                  <span>{@html sanitize(m[`ranking.methodo.methods.${card.id}.list.${i}`]())}</span>
                </li>
              {/each}
            </ul>
          </div>
        </div>
      {/each}
    </div>
  </section>

  <section class="mt-16">
    <h3 class="fr-h6 mb-4!">{m['ranking.methodo.style.title']()}</h3>
    <p class="mb-4! text-dark-grey text-[14px]!">
      {@html sanitize(m['ranking.methodo.style.desc.1']())}
    </p>
    <p class="mb-6! text-dark-grey text-[14px]!">
      {@html sanitize(m['ranking.methodo.style.desc.2']())}
    </p>

    {#if styleRows.length > 0}
      <div class="cg-border rounded-sm! bg-white p-6 max-w-[640px]">
        <h4 class="mb-1! text-lg!">{m['ranking.methodo.style.coef.title']()}</h4>
        <p class="mb-5! text-dark-grey text-[13px]!">
          {@html sanitize(m['ranking.methodo.style.coef.hint']())}
        </p>

        <ul class="m-0! p-0! list-none!">
          {#each styleRows as row (row.key)}
            <li
              class="not-last:mb-3 gap-4 pb-3 flex items-center justify-between not-last:border-b not-last:border-[--border-default-grey]"
            >
              <span class="text-[14px]">{row.label}</span>
              <span
                class={[
                  'font-mono font-bold text-[14px]',
                  row.value >= 0 ? 'text-info' : 'text-[--text-default-success]'
                ]}
              >
                {row.value >= 0 ? '+' : ''}{row.value.toFixed(3)}
              </span>
            </li>
          {/each}
        </ul>

        <p class="mt-5! mb-0! text-dark-grey text-[12px]!">
          {@html sanitize(m['ranking.methodo.style.coef.footnote']())}
        </p>
      </div>
    {/if}
  </section>

  <section class="mt-16">
    <h3 class="fr-h6 mb-4!">{m['ranking.methodo.impacts.title']()}</h3>

    <div class="gap-6 lg:grid-cols-2 grid">
      <div class="max-w-[528px]">
        <h4 class="mb-5! leading-normal! lg:mb-10! text-[14px]!">
          {m['ranking.methodo.impacts.winrate.title']()}
        </h4>

        <div>
          <div class="rounded-sm bg-white h-[400px]">
            <WinHistogram
              id="histogram-winrate"
              title={m['ranking.methodo.impacts.winrate.title']()}
              data={modelsData['win_rate']}
              {minMaxY}
            />
          </div>
          <div class="mb-5 mt-2 gap-5 flex">
            <!-- <Link
              href="FIXME"
              text={m['actions.accessData']()}
              class="text-[14px]! text-dark-grey!"
            /> -->

            <Link
              href="#"
              download="true"
              text={m['actions.downloadData']()}
              icon="download-line"
              iconPos="right"
              class="text-dark-grey! bg-none! text-[14px]! no-underline!"
              onclick={() => onDownloadData()}
            />
          </div>
        </div>

        <p class="text-[14px]!">
          {@html sanitize(m['ranking.methodo.impacts.winrate.desc.1']())}
        </p>
        <p class="text-[14px]!">{m['ranking.methodo.impacts.winrate.desc.2']()}</p>
      </div>

      <div class="max-w-[528px]">
        <h4 class="mb-5! leading-normal! text-[14px]!">
          {m['ranking.methodo.impacts.elo.title']()}
        </h4>

        <div>
          <div class="rounded-sm bg-white h-[400px]">
            <WinHistogram
              id="histogram-elo"
              title={m['ranking.methodo.impacts.elo.title']()}
              data={modelsData['mean_win_prob']}
              {minMaxY}
            />
          </div>
          <div class="mb-5 mt-2 gap-5 flex">
            <!-- <Link
              href="FIXME"
              text={m['actions.accessData']()}
              class="text-[14px]! text-dark-grey!"
            /> -->

            <Link
              href="#"
              download="true"
              text={m['actions.downloadData']()}
              icon="download-line"
              iconPos="right"
              class="text-dark-grey! bg-none! text-[14px]! no-underline!"
              onclick={() => onDownloadData()}
            />
          </div>
        </div>

        <p class="text-[14px]!">
          {@html sanitize(m['ranking.methodo.impacts.elo.desc.1']())}
        </p>
      </div>
    </div>
  </section>

  <section class="mt-16">
    <h3 class="fr-h6 mb-4!">{m['ranking.methodo.personal.title']()}</h3>
    <p class="mb-6! text-dark-grey text-[14px]!">
      {@html sanitize(m['ranking.methodo.personal.desc.1']())}
    </p>

    <div class="cg-border rounded-sm! bg-white p-6 max-w-[640px]">
      <p class="mb-3! font-mono font-bold text-[15px]!">score = (points + 2m) / (battles + 2)</p>
      <p class="mb-0! text-dark-grey text-[13px]!">
        {@html sanitize(m['ranking.methodo.personal.desc.2']())}
      </p>
    </div>

    <ul class="mt-6! m-0! p-0! max-w-[640px] list-none!">
      {#each ['both_good', 'both_bad', 'idk'] as const as choice (choice)}
        <li class="not-last:mb-3 pb-3 p-0!">
          <span class="text-[14px]"
            >{@html sanitize(m[`ranking.methodo.personal.choices.${choice}`]())}</span
          >
        </li>
      {/each}
    </ul>
  </section>
</div>
