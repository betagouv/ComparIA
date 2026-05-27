<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import EnergyLabel from '$components/EnergyLabel.svelte'
  import HardwareScale from '$components/HardwareScale.svelte'
  import TierBand from '$components/TierBand.svelte'
  import { Badge, Button, Icon, Link } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import type { BotModel } from '$lib/models'
  import { getModelExtras, type Modality } from '$lib/mockModelExtras'

  let { model, modalId, onClose }: { model?: BotModel; modalId: string; onClose?: () => void } =
    $props()

  // NOTE (mockup): all the visible strings below are STATIC French labels. In the
  // current card the equivalent text is `desc`/`size_desc`/`fyi` — free prose that
  // must be translated for every model in every language. Here only these few UI
  // labels would ever need translating, never the per-model content.

  const badges = $derived.by(() => {
    if (!model) return []
    const { releaseDate } = model.badges
    return [releaseDate].filter((b) => !!b)
  })

  const extras = $derived(model ? getModelExtras(model) : null)

  // Short code + full label for the architecture chip. "maybe-*" archs are estimated.
  const ARCH_LABELS: Record<string, { short: string; full: string }> = {
    moe: { short: 'MoE', full: "Mélange d'experts" },
    'maybe-moe': { short: 'MoE', full: "Mélange d'experts (estimé)" },
    dense: { short: 'Dense', full: 'Architecture dense' },
    'maybe-dense': { short: 'Dense', full: 'Architecture dense (estimée)' },
    matformer: { short: 'Matformer', full: 'Matformer' },
    'maybe-matformer': { short: 'Matformer', full: 'Matformer (estimé)' },
    na: { short: 'N.C.', full: 'Non communiquée' }
  }

  const MODALITIES: { id: Modality; icon: string; label: string }[] = [
    { id: 'text', icon: 'i-ri-file-text-line', label: 'Texte' },
    { id: 'image', icon: 'i-ri-image-line', label: 'Image' },
    { id: 'audio', icon: 'i-ri-volume-up-line', label: 'Audio' },
    { id: 'video', icon: 'i-ri-film-line', label: 'Vidéo' }
  ]

  const nf = new Intl.NumberFormat('fr-FR')

  const dsfrEvents = {
    'ondsfr.conceal': () => onClose?.()
  }
</script>

{#snippet statTile(value: string, label: string, sub?: string, hint?: string)}
  <div
    class="cg-border flex h-full flex-col items-center justify-center bg-white px-3 py-4 text-center"
  >
    {#if hint}
      <span class="-mb-1 self-end" title={hint}>
        <Icon icon="i-ri-question-line" size="xs" class="text-grey" />
      </span>
    {/if}
    <span class="text-dark-grey text-2xl! font-bold leading-tight">{value}</span>
    <span class="text-grey mt-1 text-xs! leading-snug">{label}</span>
    {#if sub}
      <span class="text-grey mt-2 border-t border-[--grey-925-125] pt-2 text-xs! leading-snug">
        {sub}
      </span>
    {/if}
  </div>
{/snippet}

{#snippet specChip(label: string, icon: string, value: string, sub?: string, hint?: string)}
  <div class="cg-border flex h-full flex-col bg-white p-3">
    <div class="mb-1 flex items-center gap-1">
      <Icon {icon} size="xs" class="text-info" />
      <span class="text-grey text-xs!">{label}</span>
      {#if hint}
        <span class="ms-auto" title={hint}>
          <Icon icon="i-ri-question-line" size="xs" class="text-grey" />
        </span>
      {/if}
    </div>
    <span class="text-dark-grey text-sm! font-bold leading-tight">{value}</span>
    {#if sub}
      <span class="text-grey mt-[2px] text-xs! leading-snug">{sub}</span>
    {/if}
  </div>
{/snippet}

{#snippet sovRow(label: string, value: string, tone: 'positive' | 'negative' | 'neutral')}
  <div class="flex items-baseline justify-between gap-3 border-b border-[--grey-925-125] py-[10px]">
    <span class="text-grey text-sm!">{label}</span>
    <span
      class={[
        'text-sm! font-bold',
        {
          'text-green': tone === 'positive',
          'text-red': tone === 'negative',
          'text-dark-grey': tone === 'neutral'
        }
      ]}
    >
      {value}
    </span>
  </div>
{/snippet}

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

          {#if model && extras}
            <div class="fr-modal__content">
              <h5
                id="{modalId}-title"
                class="mb-3! text-lg! text-dark-grey flex items-center gap-2 font-normal!"
              >
                <AILogo iconPath={model.icon_path} size="lg" alt={model.organisation} />
                <div>
                  {model.organisation}/<span class="font-extrabold">{model.simple_name}</span>
                </div>
              </h5>

              <ul class="fr-badges-group mb-5!">
                {#each badges as badge, i (i)}
                  <li><Badge id="general-badge-{i}" {...badge} /></li>
                {/each}
              </ul>

              <div class="gap-5 lg:flex-row flex flex-col">
                <!-- LEFT COLUMN -->
                <div class="gap-5 flex flex-col lg:basis-3/5">
                  <!-- Technical characteristics -->
                  <section class="cg-border bg-white p-4 pb-6">
                    <h6 class="mb-4! text-lg! flex items-center">
                      <Icon icon="i-ri-ruler-line" block class="text-info me-2" />
                      Caractéristiques techniques
                    </h6>

                    <!-- Hero quantities -->
                    <div class="gap-3 sm:grid-cols-2 mb-3 grid grid-cols-1">
                      {@render statTile(
                        `${nf.format(model.params)} mds.`,
                        'de paramètres',
                        model.active_params ? `${nf.format(model.active_params)} mds. actifs` : undefined,
                        model.distribution === 'api-only' ? 'Taille estimée — non communiquée par l’éditeur' : undefined
                      )}
                      {@render statTile(
                        nf.format(extras.contextWindow),
                        'jetons de contexte',
                        `env. ${nf.format(extras.contextChars)} caractères`,
                        'Quantité de texte traitable en une seule requête'
                      )}
                    </div>

                    <!-- Categorical specs -->
                    <div class="gap-3 sm:grid-cols-3 grid grid-cols-1">
                      {@render specChip(
                        'Architecture',
                        'i-ri-stack-line',
                        (ARCH_LABELS[model.arch] ?? ARCH_LABELS.na).short,
                        (ARCH_LABELS[model.arch] ?? ARCH_LABELS.na).full,
                        'Organisation interne du modèle'
                      )}

                      <div class="cg-border flex h-full flex-col bg-white p-3">
                        <div class="mb-1 flex items-center gap-1">
                          <Icon icon="i-ri-shapes-line" size="xs" class="text-info" />
                          <span class="text-grey text-xs!">Modalités d'entrée</span>
                        </div>
                        <div class="mt-1 flex items-center gap-3">
                          {#each MODALITIES as mod (mod.id)}
                            {@const on = extras.inputModalities.includes(mod.id)}
                            <span
                              class="flex flex-col items-center gap-[2px]"
                              title="{mod.label}{on ? '' : ' — non pris en charge'}"
                            >
                              <Icon
                                icon={mod.icon}
                                size="sm"
                                class={on ? 'text-dark-grey' : 'text-grey opacity-30'}
                              />
                              <span class={['text-[10px]!', on ? 'text-grey' : 'text-grey opacity-40']}>
                                {mod.label}
                              </span>
                            </span>
                          {/each}
                        </div>
                      </div>

                      {@render specChip(
                        'Connaissances',
                        'i-ri-calendar-line',
                        extras.knowledgeCutoff ? `jusqu'à ${extras.knowledgeCutoff}` : 'Non communiqué',
                        undefined,
                        'Date approximative de fin des données d’entraînement'
                      )}
                    </div>
                  </section>

                  <!-- Environmental impact -->
                  <section class="cg-border bg-white p-4 pb-6">
                    <h6 class="mb-4! text-lg! flex items-center">
                      <Icon icon="i-ri-leaf-line" block class="text-green me-2" />
                      Impact environnemental
                    </h6>

                    <div class="gap-3 sm:grid-cols-2 grid grid-cols-1">
                      <div class="cg-border flex flex-col bg-white p-4">
                        <div class="mb-3 flex items-center gap-1">
                          <Icon icon="i-ri-cpu-line" size="xs" class="text-info" />
                          <span class="text-grey text-xs!">Matériel nécessaire</span>
                          <span
                            class="ms-auto"
                            title="Estimé à partir de la mémoire requise par le modèle (~80 Go par carte graphique)."
                          >
                            <Icon icon="i-ri-question-line" size="xs" class="text-grey" />
                          </span>
                        </div>
                        <HardwareScale tier={extras.hardware} gpuCount={extras.gpuCount} />
                      </div>

                      <div class="cg-border flex flex-col bg-white p-4">
                        <div class="mb-3 flex items-center gap-1">
                          <span class="text-grey text-xs!">Classe de consommation énergétique</span>
                          <span title="Estimée via EcoLogits, en Wh par million de jetons">
                            <Icon icon="i-ri-question-line" size="xs" class="text-grey" />
                          </span>
                        </div>
                        <div class="gap-4 flex flex-1 flex-col justify-center">
                          <EnergyLabel value={extras.energyClass} />
                          {#if extras.energyNotes.length}
                            <ul class="gap-x-4 gap-y-1 flex flex-wrap justify-center">
                              {#each extras.energyNotes as note (note.label)}
                                <li class="text-dark-grey flex items-center gap-1.5 text-xs!">
                                  <span>{note.positive ? '👍' : '👎'}</span>
                                  <span>{note.label}</span>
                                </li>
                              {/each}
                            </ul>
                          {/if}
                        </div>
                      </div>
                    </div>
                  </section>

                  <!-- Sources -->
                  <section class="cg-border bg-white p-4 pb-6">
                    <h6 class="mb-3! text-lg! flex items-center">
                      <Icon icon="i-ri-link" block class="me-2" />
                      Plus d'informations et sources
                    </h6>

                    <div class="gap-x-8 gap-y-1 sm:grid-cols-2 grid grid-cols-1">
                      {#if extras.sources.huggingface}
                        <Link size="sm" href={extras.sources.huggingface} text="Hugging Face" />
                      {/if}
                      {#if extras.sources.official}
                        <Link size="sm" href={extras.sources.official} text="Site officiel du modèle" />
                      {/if}
                      <Link size="sm" href={extras.sources.modelCard ?? '#'} text="Fiche modèle" />
                      <Link
                        size="sm"
                        href={extras.sources.artificialAnalysis}
                        text="Artificial Analysis"
                      />
                      <Link
                        size="sm"
                        href="https://huggingface.co/spaces/genai-impact/ecologits-calculator"
                        text="EcoLogits"
                      />
                      <Link size="sm" href="https://impactco2.fr" text="Impact CO₂" />
                    </div>
                  </section>
                </div>

                <!-- RIGHT COLUMN -->
                <div class="gap-5 flex flex-col lg:basis-2/5">
                  <!-- Openness & sovereignty -->
                  <section class="cg-border bg-white p-4 pb-5">
                    <h6 class="mb-3! text-lg! flex items-center">
                      <Icon icon="i-ri-government-line" block class="text-primary me-2" />
                      Ouverture et souveraineté
                      <Badge
                        {...model.badges.license}
                        size="sm"
                        class="ms-auto self-center!"
                      />
                    </h6>

                    <div>
                      {@render sovRow('Licence', extras.licenseLabel, 'neutral')}
                      {@render sovRow(
                        'Poids du modèle',
                        extras.weights,
                        extras.weightsPositive ? 'positive' : 'negative'
                      )}
                      {@render sovRow(
                        'Réutilisation des sorties',
                        extras.reuseLabel,
                        extras.reusePositive ? 'positive' : 'negative'
                      )}
                      {@render sovRow(
                        'Usage commercial',
                        extras.commercialLabel,
                        extras.commercialPositive ? 'positive' : 'negative'
                      )}
                      {@render sovRow(
                        "Jeux de données d'entraînement",
                        extras.trainingDataLabel,
                        extras.trainingDataPositive ? 'positive' : 'negative'
                      )}
                      {@render sovRow(
                        "Code d'entraînement",
                        extras.trainingCodeLabel,
                        extras.trainingCodePositive ? 'positive' : 'negative'
                      )}
                      {@render sovRow(
                        "Pays d'origine de l'éditeur",
                        `${extras.country.flag} ${extras.country.code}`,
                        'neutral'
                      )}
                      <div class="flex items-baseline justify-between gap-3 py-[10px]">
                        <span class="text-grey flex items-center gap-1 text-sm!">
                          Hébergeable dans l'UE
                          <span
                            class="self-center"
                            title="Au moins un hébergeur propose ce modèle depuis un centre de données situé dans l'Union européenne."
                          >
                            <Icon icon="i-ri-question-line" size="xs" class="text-grey" />
                          </span>
                        </span>
                        <span
                          class={[
                            'text-sm! font-bold',
                            extras.euHosting ? 'text-green' : 'text-red'
                          ]}
                        >
                          {extras.euHosting ? 'Oui' : 'Non'}
                        </span>
                      </div>
                    </div>
                  </section>

                  <!-- Ranking performance -->
                  <section class="cg-border bg-white p-4 pb-6">
                    <h6 class="mb-1! text-lg! flex items-center">
                      <Icon icon="i-ri-trophy-line" block class="text-yellow me-2" />
                      Performances au classement
                    </h6>
                    <div class="mb-4">
                      <div class="mb-2 flex items-baseline justify-between gap-2">
                        <span class="text-grey flex items-center gap-1 text-xs!">
                          Niveau de performance
                          <span
                            class="self-center"
                            title="Regroupement des modèles par niveau de performance, repris du classement général."
                          >
                            <Icon icon="i-ri-question-line" size="xs" class="text-grey" />
                          </span>
                        </span>
                        <span class="text-dark-grey text-sm! font-bold">Tier {extras.tier}</span>
                      </div>
                      <TierBand value={extras.tier} />
                    </div>

                    <div class="gap-3 grid grid-cols-3">
                      {@render statTile(
                        `#${extras.rank}`,
                        'au classement général',
                        `sur ${extras.totalRanked} modèles`,
                        'Position de ce modèle dans le classement général de l’arène'
                      )}
                      {@render statTile(
                        nf.format(extras.btScore),
                        'score Bradley-Terry',
                        `± ${extras.btInterval}`,
                        'Note de force estimée à partir des duels, façon Elo. La marge indique l’incertitude.'
                      )}
                      {@render statTile(
                        nf.format(extras.votes),
                        'votes enregistrés',
                        undefined,
                        'Nombre de comparaisons impliquant ce modèle'
                      )}
                    </div>
                  </section>
                </div>
              </div>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</dialog>
