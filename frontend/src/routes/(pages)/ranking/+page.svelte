<script lang="ts">
  import SeoHead from '$lib/components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import { propsToAttrs, sanitize } from '$lib/utils/commons'
  import RankingTable from './components/RankingTable.svelte'
</script>

<SeoHead title={m['seo.titles.ranking']()} />

<main class="pb-30 bg-light-grey pt-12">
  <div class="fr-container">
    <h1 class="fr-h3 mb-10!">{m['ranking.title']()}</h1>

    <p>
      {@html sanitize(
        m['ranking.desc']({
          linkProps: propsToAttrs({ href: '#FIXME', class: 'text-primary!' })
        })
      )}
    </p>

    <RankingTable />
  </div>
</main>
