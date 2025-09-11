<script lang="ts">
  import { Button, Checkbox, Icon } from '$components/dsfr'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
  import { m } from '$lib/i18n/messages'
  import { propsToAttrs } from '$lib/utils/commons'

  const acceptTos = useLocalStorage('comparia:tos', false)
  let showModal = $state(!acceptTos.value)
  let tosError = $state<string>()

  $effect(() => {
    if (acceptTos.value) tosError = undefined
  })

  function onClose(e: MouseEvent) {
    if (!acceptTos.value) {
      e.stopPropagation()
      tosError = m['home.intro.tos.error']()
    }
  }

  const pratices = [
    { label: 'welcome.errors', icon: 'success-line' },
    { label: 'welcome.privacy', icon: 'pass-expired-line' },
    { label: 'welcome.use', icon: 'chat-delete-line' }
  ] as const
</script>

<button class="hidden" data-fr-opened={showModal} aria-controls="fr-modal-welcome"> Hidden </button>
<dialog
  aria-labelledby="fr-modal-title-modal-welcome"
  id="fr-modal-welcome"
  class="fr-modal"
  data-fr-concealing-backdrop="false"
>
  <div class="fr-container fr-container--fluid fr-container-md">
    <div class="fr-grid-row fr-grid-row--center">
      <div class="fr-col-12 fr-col-md-8 fr-col-lg-9">
        <div class="fr-modal__body rounded-xl">
          <div class="fr-modal__content mb-0! px-0!">
            <div class="grid-cols-2 md:grid">
              <div class="px-7 pb-7 pt-10">
                <h2 id="fr-modal-title-modal-welcome" class="fr-modal__title mb-0! text-primary!">
                  {m['welcome.title']()}
                </h2>
              </div>
              <div class="bg-light-grey hidden md:block"></div>
            </div>

            <div class="grid-cols-2 md:grid">
              <div class="px-7">
                {#each pratices as { label, icon }}
                  <div class="mb-7 md:last-of-type:mb-0">
                    <Icon {icon} block size="lg" class="text-primary me-2" />
                    <p class="mb-0! text-[14px]!">{m[label]()}</p>
                  </div>
                {/each}
              </div>
              <div class="bg-light-grey px-7 pt-7 md:pt-0">
                <p class="mb-2!"><strong>{m['home.intro.tos.help']()}</strong></p>
                <p class="mb-0! text-[14px]!">{m['welcome.tos.desc']()}</p>
                <p class="text-[14px]!">
                  <a href="/product/problem" target="_blank">{m['welcome.tos.moreInfos']()}</a>
                </p>

                <Checkbox
                  bind:checked={acceptTos.value}
                  id="tos-modal"
                  label={m['home.intro.tos.accept']({
                    linkProps: propsToAttrs({ href: '/modalites', target: '_blank' })
                  })}
                  error={tosError}
                  class={{ 'mb-0!': !tosError }}
                />
              </div>
            </div>

            <div class="grid-cols-2 md:grid">
              <div class="hidden md:block"></div>
              <div class="bg-light-grey flex justify-end px-7 py-7">
                <Button
                  text={m['welcome.go']()}
                  aria-controls="fr-modal-welcome"
                  onclickcapture={(e) => onClose(e)}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>
