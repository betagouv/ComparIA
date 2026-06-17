<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Button, Icon } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import type { BotModel } from '$lib/models'

  let { model, modalId, onClose }: { model?: BotModel; modalId: string; onClose?: () => void } =
    $props()

  const badges = $derived.by(() => {
    if (!model) return []
    const { release } = model.badges
    return [release].filter((b) => !!b)
  })

  const dsfrEvents = {
    'ondsfr.conceal': () => onClose?.()
  }
</script>

<button class="hidden" data-fr-opened={!!model} aria-controls={modalId}>Hidden</button>

<dialog
  aria-labelledby="{modalId}-title"
  id={modalId}
  class="fr-modal before:h-[5vh]! before:basis-[5vh]! after:h-[5vh]! after:basis-[5vh]!"
  {...dsfrEvents}
>
  <div class="fr-container fr-container--fluid">
    <div class="fr-grid-row fr-grid-row--center">
      <div class="fr-col-12 fr-col-md-12 fr-col-lg-12">
        <div
          class="fr-modal__body bg-light-grey! lg:max-h-[90vh]! dark:border-grey! rounded-xl dark:border!"
        >
          <div class="fr-modal__header pb-0!">
            <Button
              variant="tertiary-no-outline"
              text={m['words.close']()}
              title={m['closeModal']()}
              aria-controls={modalId}
              class="fr-btn--close"
            />
          </div>

          {#if model}
            <div class="fr-modal__content">
              <h5
                id="{modalId}-title"
                class="mb-3! text-lg! font-normal! text-dark-grey gap-2 flex items-center"
              >
                <AILogo logo={model.lab.logo} size="lg" alt={model.lab.name} />
                <div>
                  {model.lab.name}/<span class="font-extrabold">{model.name}</span>
                </div>
              </h5>

              <ul class="fr-badges-group mb-4!">
                {#each badges as badge, i (i)}
                  <li><Badge id="general-badge-{i}" {...badge} /></li>
                {/each}
              </ul>

              <div class="gap-5 lg:grid-cols-8 grid">
                <div class="cg-border bg-white p-4 pb-6 lg:col-span-4">
                  <div class="mb-4 flex">
                    <h6 class="mb-0! text-lg! flex">
                      <Icon icon="i-ri-ruler-line" block class="text-info me-2" />
                      {m['models.size.title']()}
                    </h6>
                    <Badge {...model.badges.size} size="sm" class="ms-auto self-center!" />
                  </div>

                  <div class="fr-message block!"></div>
                </div>

                <div class="cg-border bg-white p-4 pb-6 lg:col-span-4">
                  <div class="mb-4 flex">
                    <h6 class="mb-0! text-lg! flex">
                      <Icon icon="i-ri-lightbulb-line" block class="text-yellow me-2" />
                      {m['models.arch.title']()}
                    </h6>
                    <Badge
                      {...model.badges.arch}
                      id={modalId + '-arch'}
                      size="sm"
                      class="ms-auto self-center!"
                    />
                  </div>

                  <div class="fr-message block!"></div>
                </div>

                <div class="cg-border bg-white p-4 pb-6 lg:col-span-2">
                  <h6 class="mb-2! text-sm! flex">
                    <Icon icon="i-ri-link" block class="me-2" />
                    {m['models.extra.title']()}
                  </h6>
                </div>
              </div>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</dialog>
