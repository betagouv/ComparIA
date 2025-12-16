<script lang="ts">
  import Badge from '$components/dsfr/Badge.svelte'
  import { m } from '$lib/i18n/messages'
  import { externalLinkProps, propsToAttrs, sanitize } from '$lib/utils/commons'

  const steps = (
    [
      {
        key: 'i18n',
        items: [
          { index: '6', vote: true },
          {
            index: '5',
            noDate: true,
            title: m[`product.history.steps.i18n.items.5.title`]({
              linkProps: externalLinkProps('https://www.digitalpublicgoods.net/r/comparia')
            })
          },
          {
            index: '4',
            noDate: true,
            title: m[`product.history.steps.i18n.items.4.title`]({
              linkProps: externalLinkProps('https://ai-arenaen.dk/')
            })
          },
          {
            index: '3',
            noDate: true,
            title: m[`product.history.steps.i18n.items.3.title`]({
              linkProps: propsToAttrs({ href: '/ranking' })
            }),
            desc: m[`product.history.steps.i18n.items.3.desc`]({
              linkProps: externalLinkProps('https://www.peren.gouv.fr/')
            })
          },
          {
            index: '2',
            title: m[`product.history.steps.i18n.items.2.title`]({
              linkProps: propsToAttrs({ href: '/duel' })
            })
          },
          { index: '1' }
        ]
      },
      {
        key: 'acceleration',
        items: [
          {
            index: '3',
            desc: m[`product.history.steps.acceleration.items.3.desc`]({
              hgLinkProps: externalLinkProps('https://huggingface.co/comparIA'),
              dataLinkProps: externalLinkProps('https://www.data.gouv.fr/datasets/compar-ia/')
            })
          },
          {
            index: '2',
            vote: true,
            desc: m[`product.history.steps.acceleration.items.2.desc`]({
              linkProps: externalLinkProps('https://monitor.bunka.ai/compar:ia')
            })
          },
          { index: '1', vote: true }
        ]
      },
      {
        key: 'construction',
        items: [
          {
            index: '4',
            title: m[`product.history.steps.construction.items.4.title`]({
              linkProps: propsToAttrs({ href: '/news/bnf' })
            })
          },
          { index: '3' },
          { index: '2' },
          { index: '1' }
        ]
      },
      { key: 'investigation', items: [{ index: '1' }] }
    ] as const
  ).map((step) => {
    return {
      ...step,
      tag: m[`product.history.steps.${step.key}.tag`](),
      items: step.items.map((item) => {
        const baseKey = `product.history.steps.${step.key}.items.${item.index}` as const
        return {
          // @ts-expect-error i18n
          date: !item.noDate ? m[`${baseKey}.date`]() : null,
          // @ts-expect-error i18n
          special: item.vote,
          // @ts-expect-error i18n
          title: item.title ?? m[`${baseKey}.title`](),
          // @ts-expect-error i18n
          desc: item.desc ?? m[`${baseKey}.desc`]()
        }
      })
    }
  })
</script>

<div>
  <h2 class="fr-h4 mb-12!">{m['product.history.title']()}</h2>

  {#each steps as step (step.key)}
    <div class="pb-8 relative">
      <div class="md:ms-[196px]">
        <Badge
          text={step.tag}
          variant="blue-ecume"
          class="mb-6 md:ms-4 text-[--blue-france-sun-113-625]!"
        />
      </div>

      {#each step.items as item, i (`${step.key}-${i}`)}
        {#if item.date}
          <p class="ms-7! font-bold md:hidden">{item.date}</p>
        {/if}
        <div class="gap-4 flex">
          <div class="gap-4 md:w-[196px] md:min-w-[196px] flex">
            {#if item.date}
              <p class="font-bold md:block hidden w-full text-end">{item.date}</p>
            {/if}
            <div
              class={[
                'md:ms-auto z-1 h-[26px] w-[26px] min-w-[26px] rounded-full border-3',
                item.special
                  ? 'border-[#FFCC00] bg-[--green-tilleul-verveine-975-75]'
                  : 'border-primary bg-white'
              ]}
            ></div>
          </div>
          <div class="mb-10 max-w-[620px]">
            <p class="mb-1!"><strong>{@html sanitize(item.title)}</strong></p>
            <p class="mb-0! text-sm! leading-normal! text-grey">{@html sanitize(item.desc)}</p>
          </div>
        </div>
      {/each}

      <div
        class="top-14 md:left-[182px] absolute left-[12px] h-full border-s-2 border-dashed border-[#CECECE]"
        class:hidden={step.key === 'investigation'}
      ></div>
    </div>
  {/each}
</div>
