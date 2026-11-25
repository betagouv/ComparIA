<script lang="ts">
  import CookieBanner from '$components/CookieBanner.svelte'
  import type { CookieBanner as CookieBannerText } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'

  let {
    title,
    description,
    audience_measurement_label,
    audience_measurement_description,
    remembered_settings_label,
    remembered_settings_description
  }: Partial<CookieBannerText> = $props()

  const text = $derived({
    title: title || m['admin.legal.cookies.bannerTitle'](),
    description: description || m['admin.legal.cookies.description'](),
    audience_measurement_label:
      audience_measurement_label || m['admin.legal.cookies.audienceMeasurementLabel'](),
    audience_measurement_description:
      audience_measurement_description || m['admin.legal.cookies.audienceMeasurementDescription'](),
    remembered_settings_label:
      remembered_settings_label || m['admin.legal.cookies.rememberedSettingsLabel'](),
    remembered_settings_description:
      remembered_settings_description || m['admin.legal.cookies.rememberedSettingsDescription']()
  })
</script>

<div data-testid="cookie-banner-preview">
  <CookieBanner {text} preview />
</div>
