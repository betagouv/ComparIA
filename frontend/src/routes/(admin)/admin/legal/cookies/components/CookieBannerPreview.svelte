<script lang="ts">
  import { Button } from '$components/dsfr'
  import type { CookieBanner } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'

  // FIXME replace with the real banner component once it lands
  let {
    title,
    description,
    audience_measurement_label,
    audience_measurement_description,
    remembered_settings_label,
    remembered_settings_description
  }: Partial<CookieBanner> = $props()

  const kinds = $derived([
    {
      id: 'audience_measurement',
      label: audience_measurement_label || m['admin.legal.cookies.audienceMeasurementLabel'](),
      description:
        audience_measurement_description ||
        m['admin.legal.cookies.audienceMeasurementDescription']()
    },
    {
      id: 'remembered_settings',
      label: remembered_settings_label || m['admin.legal.cookies.rememberedSettingsLabel'](),
      description:
        remembered_settings_description || m['admin.legal.cookies.rememberedSettingsDescription']()
    }
  ])
</script>

<div data-testid="cookie-banner-preview" class="fr-card fr-card--shadow fr-p-4w bg-white">
  <h3 class="fr-h4 text-primary!">{title || m['admin.legal.cookies.bannerTitle']()}</h3>
  <p class="fr-text--sm">{description || m['admin.legal.cookies.description']()}</p>

  <ul class="fr-text--sm ps-0! list-none">
    {#each kinds as kind (kind.id)}
      <li class="mb-3">
        <strong class="block">{kind.label}</strong>
        {kind.description}
      </li>
    {/each}
  </ul>

  <div class="gap-3 flex flex-wrap">
    <Button text={m['cookieBanner.acceptAll']()} disabled />
    <Button text={m['cookieBanner.refuseAll']()} disabled />
    <Button text={m['cookieBanner.choose']()} disabled />
  </div>
</div>
