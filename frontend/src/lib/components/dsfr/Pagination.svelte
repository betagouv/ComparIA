<script lang="ts">
  type PaginationProps = {
    page: number
    itemCount: number
    maxItemPerPage?: number
  }

  let { page = $bindable(), itemCount, maxItemPerPage = 10 }: PaginationProps = $props()

  const pageCount = $derived(Math.ceil(itemCount / maxItemPerPage))
  const pages = $derived(
    [page - 1, page, page + 1]
      .map((n) => {
        return page === 0 ? n + 1 : page === pageCount - 1 ? n - 1 : n
      })
      .filter((n) => n < pageCount)
  )
</script>

{#if pageCount > 1}
  <nav
    class="fr-pagination"
    aria-label="Pagination"
    data-fr-analytics-page-total={pageCount}
  >
    <ul class="fr-pagination__list">
      <li>
        <a
          class="fr-pagination__link fr-pagination__link--first"
          title="Première page"
          {...page === 0
            ? { role: 'link', 'aria-disabled': 'true' }
            : { href: `#0`, onclick: () => (page = 0) }}
        >
          Première page
        </a>
      </li>
      <li>
        <a
          class="fr-pagination__link fr-pagination__link--prev fr-pagination__link--lg-label"
          title="Page précédente"
          {...page === 0
            ? { role: 'link', 'aria-disabled': 'true' }
            : { href: `#0`, onclick: () => page-- }}
        >
          Page précédente
        </a>
      </li>

      {#each pages as pageNumber (pageNumber)}
        <li>
          <a
            class="fr-pagination__link"
            aria-current={pageNumber === page ? 'page' : undefined}
            title="Page {pageNumber}"
            href="#{pageCount}"
            onclick={() => (page = pageNumber)}
          >
            {pageNumber + 1}
          </a>
        </li>
      {/each}

      <li>
        <a
          class="fr-pagination__link fr-pagination__link--next fr-pagination__link--lg-label"
          title="Page suivante"
          {...page >= pageCount - 1
            ? { role: 'link', 'aria-disabled': 'true' }
            : { href: `#${page - 1}`, onclick: () => page++ }}
        >
          Page suivante
        </a>
      </li>
      <li>
        <a
          class="fr-pagination__link fr-pagination__link--last"
          title="Dernière page"
          {...page === pageCount - 1
            ? { role: 'link', 'aria-disabled': 'true' }
            : { href: `#${pageCount - 1}`, onclick: () => (page = pageCount - 1) }}
        >
          Dernière page
        </a>
      </li>
    </ul>
  </nav>
{/if}

<style lang="postcss">
  :root[data-fr-theme='light'] {
    .fr-pagination__link[aria-current]:not([aria-current='false']) {
      --background-active-blue-france: var(--blue-france-main-525);
    }
  }
  /* To avoid flickering at page load */
  @media (prefers-color-scheme: light) {
    :root[data-fr-theme='system'] {
      .fr-pagination__link[aria-current]:not([aria-current='false']) {
        --background-active-blue-france: var(--blue-france-main-525);
      }
    }
  }
</style>
