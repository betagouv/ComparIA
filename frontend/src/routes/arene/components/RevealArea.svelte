<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Button, Link, Tooltip } from '$components/dsfr'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import type { RevealData, EquivalenceType } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { sanitize } from '$lib/utils/commons'
  import { MiniCard } from '.'

  let { data }: { data: RevealData } = $props()

  const locale = getLocale()

  const { selected, modelsData, shareB64Data, equivalences } = data

  // Current equivalence index (for cycling through options)
  let currentEquivIndex = $state(0)
  const currentEquiv = $derived(equivalences[currentEquivIndex])
  const equivalenceType = $derived(currentEquiv.type)
  const hasMultipleEquivalences = equivalences.length > 1

  function nextEquivalence() {
    currentEquivIndex = (currentEquivIndex + 1) % equivalences.length
  }

  let shareInput: HTMLInputElement

  function copyShareLink() {
    shareInput.select()
    navigator.clipboard.writeText(shareInput.value)
    useToast(m['actions.copyLink.done'](), 2000)
  }

  // Locale-specific reference data for country/city equivalences
  const localeReferences: Record<string, { country: string; countryTwh: number; city: string; cityGwhDay: number; carbonBudgetKg: number }> = {
    fr: { country: 'france', countryTwh: 470, city: 'paris', cityGwhDay: 40, carbonBudgetKg: 9000 },
    en: { country: 'germany', countryTwh: 500, city: 'amsterdam', cityGwhDay: 10, carbonBudgetKg: 8000 },
    da: { country: 'denmark', countryTwh: 35, city: 'copenhagen', cityGwhDay: 5, carbonBudgetKg: 5500 },
    sv: { country: 'sweden', countryTwh: 130, city: 'stockholm', cityGwhDay: 8, carbonBudgetKg: 4500 }
  }

  const refs = localeReferences[locale] || localeReferences['en']

  // ============================================================================
  // EQUIVALENCES CONFIG - Add new equivalences here
  // ============================================================================
  // category: 'energy' | 'emission' | 'absorption' - determines connector text
  // unit: translation key suffix for the base unit (e.g., 'homes' -> reveal.equivalent.scaled.units.homes)
  // reference: optional key for locale-specific reference name (country/city)
  // ============================================================================
  type EquivalenceCategory = 'energy' | 'emission' | 'absorption'

  const EQUIVALENCES: Record<EquivalenceType, {
    icon: string
    color: string
    category: EquivalenceCategory
    unit: string
    reference?: 'country' | 'city'
  }> = {
    country_electricity: { icon: 'flashlight-fill', color: 'text-yellow', category: 'energy', unit: 'days', reference: 'country' },
    city_power: { icon: 'building-2-fill', color: 'text-info', category: 'energy', unit: 'days', reference: 'city' },
    european_homes: { icon: 'home-4-fill', color: 'text-success', category: 'energy', unit: 'homes' },
    nuclear_reactors: { icon: 'settings-5-fill', color: 'text-warning', category: 'energy', unit: 'reactors' },
    solar_farm_area: { icon: 'sun-fill', color: 'text-yellow', category: 'energy', unit: 'km2' },
    wind_turbines: { icon: 'windy-fill', color: 'text-info', category: 'energy', unit: 'turbines' },
    car_earth_trips: { icon: 'car-fill', color: 'text-error', category: 'emission', unit: 'trips' },
    paris_nyc_flights: { icon: 'plane-fill', color: 'text-error', category: 'emission', unit: 'flights' },
    forest_absorption: { icon: 'leaf-fill', color: 'text-success', category: 'absorption', unit: 'hectares' },
    trees_planted: { icon: 'plant-fill', color: 'text-success', category: 'absorption', unit: 'trees' },
    carbon_budget: { icon: 'user-fill', color: 'text-warning', category: 'emission', unit: 'people' },
    tgv_paris_lyon: { icon: 'train-fill', color: 'text-info', category: 'emission', unit: 'journeys' }
  }

  // Helper to get config for an equivalence type
  function getConfig(type: EquivalenceType) {
    return EQUIVALENCES[type]
  }

  // Auto-scale a value and return the scaled value with appropriate unit suffix
  // unitKey: base translation key (e.g., 'homes' -> reveal.equivalent.scaled.units.homes)
  // Options: includeThousand (for hectares), includeBillion (for trees)
  function autoScale(
    rawValue: number,
    unitKey: string,
    options: { includeThousand?: boolean; includeBillion?: boolean } = {}
  ): { value: number; unit: string } {
    const { includeThousand = false, includeBillion = false } = options

    // Capitalize first letter for prefixed units (e.g., 'homes' -> 'millionHomes')
    const capitalizedKey = unitKey.charAt(0).toUpperCase() + unitKey.slice(1)

    // Helper for dynamic translation key lookup (cast via unknown for dynamic keys)
    const getUnit = (key: string) => (m as unknown as Record<string, () => string>)[key]()

    if (includeBillion && rawValue >= 1_000_000_000) {
      return {
        value: rawValue / 1_000_000_000,
        unit: getUnit(`reveal.equivalent.scaled.units.billion${capitalizedKey}`)
      }
    }
    if (rawValue >= 1_000_000) {
      return {
        value: rawValue / 1_000_000,
        unit: getUnit(`reveal.equivalent.scaled.units.million${capitalizedKey}`)
      }
    }
    if (includeThousand && rawValue >= 1_000) {
      return {
        value: rawValue / 1_000,
        unit: getUnit(`reveal.equivalent.scaled.units.thousand${capitalizedKey}`)
      }
    }
    return {
      value: rawValue,
      unit: getUnit(`reveal.equivalent.scaled.units.${unitKey}`)
    }
  }

  // Format value with appropriate precision for display
  function formatValue(value: number): string {
    if (value >= 100) {
      return Math.round(value).toLocaleString(locale)
    } else if (value >= 10) {
      return value.toFixed(1)
    } else if (value >= 0.01) {
      return value.toFixed(2)
    } else if (value > 0) {
      return '< 0.01'
    }
    return '0'
  }

  // Calculate display value and unit based on equivalence type and locale
  function formatEquivalence(rawValue: number, type: EquivalenceType): { value: string; unit: string } {
    let result: { value: number; unit: string }

    switch (type) {
      // === Time-based equivalences (special handling) ===
      case 'country_electricity': {
        const yearFraction = rawValue / refs.countryTwh
        if (yearFraction >= 1) {
          result = { value: yearFraction, unit: m['reveal.equivalent.scaled.units.years']() }
        } else if (yearFraction * 12 >= 1) {
          result = { value: yearFraction * 12, unit: m['reveal.equivalent.scaled.units.months']() }
        } else {
          result = { value: yearFraction * 365, unit: m['reveal.equivalent.scaled.units.days']() }
        }
        break
      }

      case 'city_power': {
        const days = rawValue / refs.cityGwhDay
        if (days >= 30) {
          result = { value: days / 30, unit: m['reveal.equivalent.scaled.units.months']() }
        } else if (days >= 7) {
          result = { value: days / 7, unit: m['reveal.equivalent.scaled.units.weeks']() }
        } else {
          result = { value: days, unit: m['reveal.equivalent.scaled.units.days']() }
        }
        break
      }

      // === Locale-dependent scaling ===
      case 'carbon_budget':
        result = autoScale(rawValue / refs.carbonBudgetKg, 'people')
        break

      // === No scaling ===
      case 'nuclear_reactors':
        result = { value: rawValue, unit: m['reveal.equivalent.scaled.units.reactors']() }
        break

      case 'solar_farm_area':
        result = { value: rawValue, unit: 'km²' }
        break

      // === Standard auto-scaling with options ===
      case 'forest_absorption':
        result = autoScale(rawValue, 'hectares', { includeThousand: true })
        break

      case 'trees_planted':
        result = autoScale(rawValue, 'trees', { includeBillion: true })
        break

      // === Standard auto-scaling (million threshold only) ===
      case 'european_homes':
        result = autoScale(rawValue, 'homes')
        break

      case 'wind_turbines':
        result = autoScale(rawValue, 'turbines')
        break

      case 'car_earth_trips':
        result = autoScale(rawValue, 'trips')
        break

      case 'paris_nyc_flights':
        result = autoScale(rawValue, 'flights')
        break

      case 'tgv_paris_lyon':
        result = autoScale(rawValue, 'journeys')
        break

      default:
        result = { value: rawValue, unit: '' }
    }

    return { value: formatValue(result.value), unit: result.unit }
  }

  // Get reference name for display (country or city name)
  function getReferenceName(type: EquivalenceType): string {
    const config = getConfig(type)
    const getRef = (key: string) => (m as unknown as Record<string, () => string>)[key]()
    if (config.reference === 'country') {
      return getRef(`reveal.equivalent.scaled.references.${refs.country}`)
    } else if (config.reference === 'city') {
      return getRef(`reveal.equivalent.scaled.references.${refs.city}`)
    }
    return ''
  }

  // Get the appropriate connector based on equivalence category
  const connector = $derived(
    getConfig(equivalenceType).category === 'absorption'
      ? m['reveal.equivalent.scaled.connectorAbsorption']()
      : getConfig(equivalenceType).category === 'emission'
        ? m['reveal.equivalent.scaled.connectorCo2']()
        : m['reveal.equivalent.scaled.connectorEnergy']()
  )
</script>

<div id="reveal-area" class="fr-container mt-8! md:mt-10!" {@attach scrollTo}>
  <div class="grid gap-5 lg:grid-cols-2 lg:gap-6">
    {#each modelsData as { model, side, energy, energyUnit, tokens } (side)}
      {@const equivalenceValue = side === 'model-a' ? currentEquiv.modelAValue : currentEquiv.modelBValue}
      {@const formatted = formatEquivalence(equivalenceValue, equivalenceType)}
      {@const modelBadges = (['license', 'size', 'releaseDate'] as const)
        .map((k) => model.badges[k])
        .filter((b) => !!b)}

      <div class="cg-border flex flex-col bg-white p-5 md:p-7 md:pb-10">
        <div>
          <h5 class="fr-h6 text-dark-grey! mb-4! flex items-center gap-2">
            <AILogo iconPath={model.icon_path} size="lg" alt={model.organisation} />
            <div><span class="font-normal">{model.organisation}/</span>{model.simple_name}</div>
            {#if selected === side}
              <div
                class="bg-(--blue-france-975-75) text-primary border-primary ms-auto rounded-[3.75rem] border px-3 text-[14px] font-bold"
              >
                {m['vote.yours']()}
              </div>
            {/if}
          </h5>
          <ul class="fr-badges-group mb-4!">
            {#each modelBadges as badge, i}
              <li><Badge id="card-badge-{i}" {...badge} noTooltip /></li>
            {/each}
          </ul>

          {@html sanitize(model.desc).replaceAll('<p>', '<p class="fr-text--sm text-grey!">')}
        </div>

        <h6 class="mt-auto! mb-5! text-base!">
          {m['reveal.impacts.title']()}
          <Tooltip id="impact-{side}" text={m['reveal.impacts.tooltip']()} />
        </h6>
        <div class="flex">
          <div class="flex basis-1/2 flex-col md:basis-2/3 md:flex-row">
            <div class="relative md:w-full">
              <MiniCard
                id="params-{side}"
                value={model.params}
                desc={m['reveal.impacts.size.label']()}
                tooltip={m['models.openWeight.tooltips.params']()}
                class="z-1 -mb-2 h-full bg-white "
              >
                {m['reveal.impacts.size.count']()}
                {#if model.distribution === 'api-only'}
                  {m['reveal.impacts.size.estimated']()}
                {/if}
                {#if model.quantization === 'q8'}
                  {m['reveal.impacts.size.quantized']()}
                {/if}
              </MiniCard>
              <div
                class="cg-border rounded-sm! bg-(--beige-gris-galet-950-100) absolute z-0 flex w-full p-1 ps-3 pt-2 text-[11px] leading-normal"
              >
                <span class="text-(--beige-gris-galet-sun-407-moon-821)">
                  {model.badges.arch.text}
                </span>
                <Tooltip
                  id="{model.id}-arch-tooltip"
                  size="xs"
                  text={model.badges.arch.tooltip}
                  class="ms-auto"
                />
              </div>
            </div>

            <strong class="m-auto mb-1 text-[20px] md:mx-1 md:my-auto">×</strong>

            <MiniCard
              id="tokens-{side}"
              value={tokens}
              units={m['reveal.impacts.tokens.tokens']()}
              desc={m['reveal.impacts.tokens.label']()}
              tooltip={m['reveal.impacts.tokens.tooltip']()}
              class="md:w-full"
            />
          </div>

          <div class="flex basis-1/2 items-center md:basis-1/3">
            <strong class="m-auto">≈</strong>

            <MiniCard
              id="energy-{side}"
              value={energy.toFixed(energy < 2 ? 2 : 0)}
              units={energyUnit}
              desc={m['reveal.impacts.energy.label']()}
              icon="flashlight-fill"
              iconClass="text-info"
              tooltip={m['reveal.impacts.energy.tooltip']()}
              class="h-fit"
            />
          </div>
        </div>

        <div class="mt-9! md:mt-14! mb-5! flex items-center gap-2">
          <h6 class="text-base! mb-0!">{m['reveal.equivalent.title']()}</h6>
          {#if hasMultipleEquivalences}
            <button
              type="button"
              onclick={nextEquivalence}
              class="fr-btn--tertiary-no-outline fr-btn--sm text-grey hover:text-primary p-1!"
              title={m['reveal.equivalent.scaled.refresh']()}
              aria-label={m['reveal.equivalent.scaled.refresh']()}
            >
              <span class="fr-icon-refresh-line" aria-hidden="true"></span>
            </button>
          {/if}
        </div>
        <p class="text-sm text-grey mb-4!">{m['reveal.equivalent.scaled.premise']()} {connector}</p>
        <MiniCard
          id="scaled-{side}"
          value={formatted.value}
          units={formatted.unit}
          desc={m[`reveal.equivalent.scaled.${equivalenceType}.label`]({ reference: getReferenceName(equivalenceType) })}
          icon={getConfig(equivalenceType).icon}
          iconClass={getConfig(equivalenceType).color}
          tooltip={m[`reveal.equivalent.scaled.${equivalenceType}.tooltip`]()}
        />

        <div class="mt-7 text-center">
          <Button
            text={m['actions.seeMore']()}
            data-fr-opened="false"
            aria-controls="modal-model-reveal-{model.id}"
            size="sm"
          />
        </div>
      </div>

      <ModelInfoModal {model} modalId="modal-model-reveal-{model.id}" />
    {/each}
  </div>

  <div class="feedback py-7">
    <div class="fr-container md:max-w-[280px]! flex flex-col items-center gap-4">
      <Link
        button
        icon="edit-line"
        href="../arene/?cgu_acceptees"
        text={m['header.chatbot.newDiscussion']()}
        class="w-full! md:hidden!"
      />

      <!-- TODO missing share page, hide btn for now -->
      <!-- <Button
        icon="upload-2-line"
        variant="secondary"
        text={m['reveal.feedback.shareResult']()}
        data-fr-opened="false"
        aria-controls="share-modal"
        class="w-full!"
      /> -->
    </div>

    <dialog aria-labelledby="fr-modal-title-share-modal" id="share-modal" class="fr-modal">
      <div class="fr-container fr-container--fluid fr-container-md">
        <div class="fr-grid-row fr-grid-row--center">
          <div class="fr-col-12 fr-col-md-8 fr-col-lg-6">
            <div class="fr-modal__body rounded-xl">
              <div class="fr-modal__header">
                <Button
                  variant="tertiary-no-outline"
                  text={m['words.close']()}
                  title={m['closeModal']()}
                  aria-controls="share-modal"
                  class="fr-btn--close"
                />
              </div>
              <div class="fr-modal__content">
                <h6 class="mb-3! text-dark-grey!">
                  {m['reveal.feedback.shareResult']()}
                </h6>

                <p class="text-sm! mb-0!">
                  {m['reveal.feedback.description']()}
                </p>
                <div class="flex flex-wrap gap-3 py-8">
                  <input
                    bind:this={shareInput}
                    type="text"
                    id="share-link"
                    class="fr-col-md-8 fr-col-12 fr-input inline"
                    value="https://comparia.beta.gouv.fr/share?i={shareB64Data}"
                  />
                  <Button
                    icon="links-fill"
                    onclick={copyShareLink}
                    text={m['actions.copyLink.do']()}
                  />
                </div>
                <img
                  class="fr-responsive-img"
                  src="/share-example.png"
                  alt={m['reveal.feedback.example']()}
                  title={m['reveal.feedback.example']()}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </dialog>
  </div>
</div>

{#if ['fr', 'en'].includes(locale)}
  <section class="fr-container--fluid bg-light-info">
    <div class="fr-container">
      <div class="lg:px-15 gap-x-15 lg:gap-x-30 flex flex-col gap-y-10 py-8 md:flex-row">
        <div class="flex max-w-[350px] flex-col">
          <h5 class="font mb-3!">{m['reveal.thanks.title']()}</h5>
          <p class="mb-8!">{m['reveal.thanks.desc']()}</p>

          <Link
            button
            size="lg"
            href="/ranking"
            icon="trophy-line"
            text={m['reveal.thanks.cta']()}
            class="w-full! sm:w-auto!"
          />
        </div>

        <div class="relative flex max-w-[640px] items-start">
          <img
            src="/arena/ranking-table.png"
            class="-me-[30%] w-full max-w-[400px] rounded-xl shadow-md md:-me-[10%]"
          />
          <img
            src="/arena/ranking-graph.png"
            class="mt-[30px] w-full max-w-[300px] rounded-xl shadow-md"
          />
        </div>
      </div>
    </div>
  </section>
{/if}

<style>
  #reveal-area {
    scroll-margin-top: calc(var(--second-header-size) + 1rem);
  }
</style>
