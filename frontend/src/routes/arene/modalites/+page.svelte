<script lang="ts">
  import { resolve } from '$app/paths'
  import { Link } from '$components/dsfr'
  import SeoHead from '$components/SEOHead.svelte'
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import { getActiveTerms, type ConsentDocument } from '$lib/consent'
  import { getLocale } from '$lib/i18n/runtime'
  import { onMount } from 'svelte'

  const locale = getLocale()
  let terms = $state<ConsentDocument>()
  let error = $state('')

  function withoutLeadingTitle(content: string) {
    return content.replace(/^\s*#\s+[^\n]+(?:\n+|$)/, '')
  }

  onMount(async () => {
    try {
      terms = await getActiveTerms(locale)
    } catch {
      error = 'Les conditions d’utilisation ne peuvent pas être chargées pour le moment.'
    }
  })
</script>

<SeoHead title="Conditions générales d’utilisation" />

<main class="py-10 lg:py-15">
  <div class="fr-container max-w-[900px]">
    <h1>Conditions générales d’utilisation</h1>
    {#if error}
      <p class="fr-alert fr-alert--error" role="alert">{error}</p>
    {:else if !terms}
      <p role="status">Chargement des conditions en vigueur…</p>
    {:else}
      <p class="fr-text--sm text-grey">
        Version {terms.version}, applicable depuis le
        {new Date(terms.effectiveAt ?? terms.publishedAt ?? '').toLocaleDateString(locale)}.
      </p>
      <div class="fr-mt-6v">
        <Markdown
          message={withoutLeadingTitle(terms.content ?? '')}
          sanitize_html
          variant="document"
        />
      </div>
    {/if}

    <div class="gap-3 mt-8 flex flex-wrap">
      <Link button href={resolve('/arene')} text="Retour à l’arène" />
      <Link
        button
        variant="secondary"
        href={resolve('/arene/donnees-personnelles')}
        text="Politique de confidentialité"
      />
    </div>
  </div>
</main>
