<script lang="ts">
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'
</script>

<SeoHead title={m['seo.titles.rgesn']()} />

<main class="py-10 lg:py-15">
  <div class="fr-container">
    <h1 id="main-title" class="mb-8!">{m['general.rgesn.title']()}</h1>
    <p>{m['general.rgesn.desc']()}</p>

    <h2 id="reason" class="mt-10!">{m['general.rgesn.1.title']()}</h2>
    <p>{m['general.rgesn.1.1']()}</p>
    <p>{m['general.rgesn.1.2']()}</p>
    <p>{@html sanitize(m['general.rgesn.1.3']())}</p>
    <p>
      {@html sanitize(
        m['general.rgesn.1.4']({
          linkProps: externalLinkProps(
            'https://www.arcep.fr/demarches-et-services/professionnels/referentiel-general-ecoconception-services-numeriques.html'
          )
        })
      )}
    </p>

    <h2 id="what-is-ecoconception" class="mt-10!">{m['general.rgesn.2.title']()}</h2>
    <p>{m['general.rgesn.2.1']()}</p>
    <p>{m['general.rgesn.2.2.title']()}</p>
    <ol class="mb-6!">
      {#each ['1', '2', '3', '4'] as const as n (n)}
        <li>{m[`general.rgesn.2.2.${n}`]()}</li>
      {/each}
    </ol>
    <p>{m['general.rgesn.2.3.title']()}</p>
    <ul class="mb-6!">
      {#each ['1', '2', '3', '4'] as const as n (n)}
        <li>{m[`general.rgesn.2.3.${n}`]()}</li>
      {/each}
    </ul>
    <p>{m['general.rgesn.2.4']()}</p>

    <h2 id="strategy" class="mt-28!">{m['general.rgesn.3.title']()}</h2>
    <p>{m['general.rgesn.3.1.title']()}</p>
    <ul class="mb-6!">
      {#each ['1', '2', '3', '4', '5', '6'] as const as n (n)}
        <li>{m[`general.rgesn.3.1.${n}`]()}</li>
      {/each}
    </ul>

    <h2 id="strategy" class="mt-10!">{m['general.rgesn.4.title']()}</h2>
    <p>
      {@html sanitize(
        m['general.rgesn.4.1']({
          greenitLinkProps: externalLinkProps(
            'https://ecoresponsable.numerique.gouv.fr/publications/boite-outils/fiches/greenitanalysis/'
          ),
          ecoindexLinkProps: externalLinkProps('https://www.ecoindex.fr/')
        })
      )}
    </p>

    <h2 id="score" class="mt-10!">{m['general.rgesn.5.title']()}</h2>
    <p>
      {@html sanitize(
        m['general.rgesn.5.1.title']({
          linkProps: externalLinkProps(
            'https://ecoresponsable.numerique.gouv.fr/publications/referentiel-general-ecoconception/'
          )
        })
      )}
    </p>
    <ul class="mb-6!">
      <li class="font-bold">{m['general.rgesn.5.1.1']()}</li>
    </ul>
    <p>{m['general.rgesn.5.2']()}</p>
    <ul class="mb-6!">
      <li class="font-bold">{m['general.rgesn.5.3.title']()}</li>
      <ul class="list-decimal!">
        {#each ['1', '2', '3', '4', '5', '6', '7', '8', '9'] as const as n (n)}
          <li>{m[`general.rgesn.5.3.${n}`]()}</li>
        {/each}
      </ul>
    </ul>

    <div class="fr-tile fr-tile--sm fr-tile--download fr-enlarge-link max-w-[400px]">
      <div class="fr-tile__body">
        <div class="fr-tile__content">
          <h3 class="fr-tile__title">
            <a hreflang="fr" data-fr-assess-file download href="/general/rgesn_2025_comparIA.ods">
              {m['general.rgesn.5.4.title']()}
            </a>
          </h3>
          <p class="fr-tile__desc">{m['general.rgesn.5.4.date']()}</p>
          <p class="fr-tile__detail"></p>
        </div>
      </div>
    </div>

    <h2 id="minimal-config" class="mt-10!">{m['general.rgesn.6.title']()}</h2>
    <ul class="mb-6!">
      {#each ['1', '2', '3', '4'] as const as n (n)}
        <li>{m[`general.rgesn.6.${n}`]()}</li>
      {/each}
    </ul>

    <h2 id="improvments" class="mt-10!">{m['general.rgesn.7.title']()}</h2>
    <p>{m['general.rgesn.7.desc']()}</p>
    <ul class="mb-6!">
      {#each ['1', '2', '3', '4', '5'] as const as n (n)}
        <li>
          {#if n === '3'}
            {m['general.rgesn.7.3.title']()}
            <ul class="mb-0!">
              {#each ['1', '2'] as const as i (i)}
                <li>{m[`general.rgesn.7.3.${i}`]()}</li>
              {/each}
            </ul>
          {:else}
            {m[`general.rgesn.7.${n}`]()}
          {/if}
        </li>
      {/each}
    </ul>
  </div>
</main>
