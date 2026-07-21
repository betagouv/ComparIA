<script lang="ts">
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import PrivacyPolicyFallback from '$components/PrivacyPolicyFallback.svelte'
  import SeoHead from '$components/SEOHead.svelte'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  let loading = $state(true)
  let privacyPolicy = $state<{
    version: string
    content: string
    published_at: string
    effective_at: string
  }>()

  function withoutLeadingTitle(content: string) {
    return content.replace(/^\s*#\s+[^\n]+(?:\n+|$)/, '')
  }

  onMount(async () => {
    try {
      privacyPolicy = await api.request('/settings/legal/privacy-policy?locale=fr')
    } catch {
      privacyPolicy = undefined
    } finally {
      loading = false
    }
  })
</script>

<SeoHead title={m['seo.titles.donnees-personnelles']()} />

<main class="py-10 lg:py-15">
  <div class="fr-container max-w-[900px]">
    <h1 id="politique-de-confidentialite">Politique de confidentialité</h1>
    {#if loading}
      <p class="fr-text--sm text-grey" role="status">
        Chargement de la politique de confidentialité…
      </p>
    {:else if privacyPolicy}
      <p class="fr-text--sm text-grey">
        Version {privacyPolicy.version}, applicable depuis le
        {new Date(privacyPolicy.effective_at ?? privacyPolicy.published_at).toLocaleDateString(
          'fr-FR'
        )}.
      </p>
      <div class="fr-mt-6v fr-mb-8v">
        <Markdown
          message={withoutLeadingTitle(privacyPolicy.content)}
          sanitize_html
          variant="document"
        />
      </div>
    {:else}
      <PrivacyPolicyFallback />
    {/if}
  </div>
</main>
