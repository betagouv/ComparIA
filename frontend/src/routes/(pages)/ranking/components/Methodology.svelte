<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'

  function onDownloadData(kind: 'winrate' | 'elo') {}
</script>

<div id="ranking-methodo">
  <h2 class="fr-h6 text-primary! mb-4!">{m['ranking.methodo.title']()}</h2>
  <p class="text-[14px]! text-dark-grey mb-4!">{m['ranking.methodo.desc.1']()}</p>
  <p class="text-[14px]! text-dark-grey">
    {@html sanitize(
      m['ranking.methodo.desc.2']({
        linkProps: externalLinkProps({ href: 'FIXME', class: 'text-primary!' })
      })
    )}
  </p>

  <section class="mt-10">
    <h3 class="fr-h6 mb-5!">{m['ranking.methodo.methods.title']()}</h3>

    <div class="grid gap-6 lg:grid-cols-2">
      {#each [{ id: 'winrate', k: 'cons' }, { id: 'elo', k: 'pros' }] as const as card}
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

            <h4 class="text-lg! mb-5!">{m[`ranking.methodo.methods.${card.k}`]()}</h4>
            <ul class="list-none! p-0! m-0!">
              {#each ['1', '2', '3'] as const as i}
                <li class="p-0! not-last:mb-5 flex">
                  <Icon
                    icon={card.k === 'pros' ? 'checkbox-circle-fill' : 'close-circle-fill'}
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

    <div class="grid gap-6 lg:grid-cols-2">
      <div class="max-w-[528px]">
        <h4 class="text-[14px]! mb-5!">{m['ranking.methodo.impacts.winrate.title']()}</h4>

        <div>
          <div class="h-[200px] rounded-sm bg-white">FIXME GRAPH</div>
          <div class="mb-5 mt-2 flex gap-5">
            <Link
              href="FIXME"
              text={m['actions.accessData']()}
              class="text-[14px]! text-dark-grey!"
            />

            <Link
              href="#"
              download="true"
              text={m['actions.downloadData']()}
              icon="download-line"
              iconPos="right"
              class="text-[14px]! text-dark-grey!"
              onclick={() => onDownloadData('winrate')}
            />
          </div>
        </div>

        <p class="text-[14px]!">
          {@html sanitize(m['ranking.methodo.impacts.winrate.desc.1']())}
        </p>
        <p class="text-[14px]!">{m['ranking.methodo.impacts.winrate.desc.2']()}</p>
      </div>

      <div class="max-w-[528px]">
        <h4 class="text-[14px]! mb-5!">{m['ranking.methodo.impacts.elo.title']()}</h4>

        <div>
          <div class="h-[200px] rounded-sm bg-white">FIXME GRAPH</div>
          <div class="mb-5 mt-2 flex gap-5">
            <Link
              href="FIXME"
              text={m['actions.accessData']()}
              class="text-[14px]! text-dark-grey!"
            />

            <Link
              href="#"
              download="true"
              text={m['actions.downloadData']()}
              icon="download-line"
              iconPos="right"
              class="text-[14px]! text-dark-grey!"
              onclick={() => onDownloadData('elo')}
            />
          </div>
        </div>

        <p class="text-[14px]!">
          {@html sanitize(m['ranking.methodo.impacts.elo.desc.1']())}
        </p>
      </div>
    </div>
  </section>
</div>
