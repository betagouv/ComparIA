<script lang="ts">
  import { page } from '$app/state'
  import CookieBanner from '$components/CookieBanner.svelte'
  import type { PublicCookieBanner } from '$lib/generated/backend'
  import { getCookieConsentContext } from '$lib/stores/cookieConsent.svelte'

  // Rendered by the layout that owns the skip links, right after them, so the
  // banner sits early in the tab order without coming before them.
  const cookieConsent = getCookieConsentContext()
  const text = $derived(page.data.cookieBanner as PublicCookieBanner | null | undefined)
</script>

{#if cookieConsent.bannerOpen && text}
  <CookieBanner
    {text}
    choice={cookieConsent.choice}
    onChoice={cookieConsent.save}
    onClose={cookieConsent.choice ? cookieConsent.close : undefined}
  />
{/if}
