<script lang="ts">
  import CookieBanner from '$components/CookieBanner.svelte'
  import type { CookieBanner as CookieBannerText } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'

  let { title, description }: Partial<CookieBannerText> = $props()

  const text = $derived({
    title: title || m['admin.legal.cookies.bannerTitle'](),
    description: description || m['admin.legal.cookies.description']()
  })
</script>

<div data-testid="cookie-banner-preview">
  <CookieBanner {text} preview />
</div>
