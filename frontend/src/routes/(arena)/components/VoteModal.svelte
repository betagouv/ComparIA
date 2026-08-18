<script lang="ts">
  import { asset, resolve } from '$app/paths'
  import { Link, Modal } from '$components/dsfr'
  import Badge from '$components/dsfr/Badge.svelte'
  import Icon from '$components/dsfr/Icon.svelte'
  import { m } from '$lib/i18n/messages'

  const voteReasons = (
    [
      { i18nKey: 'prefs', src: asset('/home/prefs.svg') },
      { i18nKey: 'datasets', src: asset('/home/datasets.svg') },
      { i18nKey: 'finetune', src: asset('/home/finetune.svg') }
    ] as const
  ).map(({ i18nKey, ...reason }) => ({
    ...reason,
    title: m[`home.vote.steps.${i18nKey}.title`](),
    desc: m[`home.vote.steps.${i18nKey}.desc`]()
  }))
</script>

<Modal
  id="fr-modal-vote"
  titleId="fr-modal-title-modal-vote"
  sizeClass="fr-col-md-10"
  contentClass="mb-10!"
>
  <Badge text={m['home.vote.datasets']()} variant="light-info" class="mb-3" />
  <section>
    <div class="md:flex-row gap-4 md:gap-15 flex flex-col">
      <div class="md:max-w-[350px]">
        <h2 id="fr-modal-title-modal-vote" class="text-2xl! mb-7!">{m['home.vote.title']()}</h2>
        <p class="text-sm! lh-relaxed!">{m['vote.importantDesc']()}</p>
      </div>
      <div class="gap-5 mb-10 md:mb-0 flex flex-col">
        {#each voteReasons as reason, index (index)}
          <div class="gap-4 flex items-start">
            <img src={reason.src} alt="" width="55" height="55" />
            <div>
              <h3 class="text-sm! mb-1!">{reason.title}</h3>
              <p class="text-xs! text-grey mb-0!">{reason.desc}</p>
            </div>
          </div>
          {#if index < 2}
            <Icon icon="i-ri-arrow-down-line" block class="ms-4 text-[--grey-625-425]" />
          {/if}
        {/each}
      </div>
    </div>
    <div class="gap-5 flex items-center">
      <Link
        text={m['actions.discover']()}
        title={m['a11y.externalLink']({ text: m['actions.discover']() })}
        icon="external-link-line"
        iconPos="right"
        button
        href={resolve('/product/comparator')}
        target="_blank"
      />
      <Link
        native={false}
        text={m['actions.returnArena']()}
        aria-controls="fr-modal-vote"
        data-fr-opened="true"
        href="#"
        class="text-dark-grey!"
      />
    </div>
  </section>
</Modal>
