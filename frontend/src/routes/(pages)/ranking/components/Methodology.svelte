<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getModelsWithDataContext, type BotModelWithData } from '$lib/models'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'
  import { downloadTextFile, sortIfDefined } from '$lib/utils/data'
  import { extent } from 'd3'
  import { WinHistogram } from '.'

  const { lastUpdateDate, models: data } = getModelsWithDataContext()

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
        perenLinkProps: externalLinkProps('https://www.peren.gouv.fr/'),
        linkProps: ''
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
            { 'border-2! border-[#58B77D]!': card.k === 'pros' }
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
                    class={['me-1', card.k === 'pros' ? 'text-[#58B77D]' : 'text-[#FF9575]']}
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
    <h3 class="fr-h6 mb-4!">{m['ranking.methodo.impacts.title']()}</h3>

    <div class="gap-6 lg:grid-cols-2 grid">
      <div class="max-w-[528px]">
        <h4 class="mb-5! leading-normal! lg:mb-10! text-[14px]!">
          {m['ranking.methodo.impacts.winrate.title']()}
        </h4>

        <div>
          <div class="rounded-sm bg-white h-[400px]">
            <WinHistogram data={modelsData['win_rate']} {minMaxY} />
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
              class="text-dark-grey! text-[14px]!"
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
            <WinHistogram data={modelsData['mean_win_prob']} {minMaxY} />
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
              class="text-dark-grey! text-[14px]!"
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
    <h3 class="fr-h6 mb-4!">{m['ranking.methodo.styleControl.title']()}</h3>

    <div class="cg-border bg-white p-7 pb-8">
      <h4 class="text-lg!">{m['ranking.methodo.styleControl.what.title']()}</h4>
      <p class="font-[14px] mb-6">
        {@html sanitize(m['ranking.methodo.styleControl.what.desc']())}
      </p>

      <h4 class="text-lg!">{m['ranking.methodo.styleControl.how.title']()}</h4>
      <p class="font-[14px]">{m['ranking.methodo.styleControl.features']()}</p>
      <ul class="m-0! mb-6 p-0! list-none!">
        {#each ['1', '2', '3'] as const as i (i)}
          <li class="p-0! not-last:mb-3 flex">
            <Icon icon="i-ri-arrow-right-s-line" block class="me-1 text-primary" />
            <span>{@html sanitize(m[`ranking.methodo.styleControl.how.${i}`]())}</span>
          </li>
        {/each}
      </ul>

      <h4 class="text-lg!">{m['ranking.methodo.styleControl.why.title']()}</h4>
      <p class="font-[14px] mb-6">
        {@html sanitize(m['ranking.methodo.styleControl.why.desc']())}
      </p>

      <h4 class="text-lg!">{m['ranking.methodo.styleControl.caveats.title']()}</h4>
      <p class="font-[14px] mb-0!">
        {@html sanitize(m['ranking.methodo.styleControl.caveats.desc']())}
      </p>

      <p class="mt-6 mb-0! font-[14px]">
        {@html sanitize(
          m['ranking.methodo.styleControl.reference']({
            lmsysLinkProps: externalLinkProps('https://lmsys.org/blog/2024-08-17-style-control/')
          })
        )}
      </p>
    </div>
  </section>
</div>
