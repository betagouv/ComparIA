<script lang="ts">
  import SeoHead from '$lib/components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'
</script>

<SeoHead title={m['seo.titles.mentions-legales']()} />

<main class="lg:py-15 py-10">
  <div class="fr-container">
    <h1 id="mentions-legales" class="fr-h2">{m['general.legal.title']()}</h1>

    <h2 id="editeur" class="fr-h5">{m['general.legal.editorTitle']()}</h2>
    <p>{m['general.legal.editorDesc']()}</p>

    <h2 id="directeur-de-la-publication" class="fr-h5">{m['general.legal.directorTitle']()}</h2>
    <p>{m['general.legal.directorDesc']()}</p>

    <h2 id="hebergement-du-site" class="fr-h5">{m['general.legal.hostingTitle']()}</h2>
    <p>
      {@html sanitize(
        m['general.legal.hostingDesc']({
          linkProps: externalLinkProps('https://www.ovh.com/')
        })
      )}
    </p>

    <h2 id="accessibilite" class="fr-h5">{m['general.legal.a11yTitle']()}</h2>
    <p>{m['general.legal.a11yDesc']()}</p>

    <h2 id="signaler-un-dysfonctionnement" class="fr-h5">{m['general.legal.reportTitle']()}</h2>
    <p>{m['general.legal.reportA11y']()}</p>
    <p>{m['general.legal.reportDesc']()}</p>
    <p>
      {@html sanitize(
        m['general.legal.reportA11yDesc']({
          linkProps: externalLinkProps(
            'http://references.modernisation.gouv.fr/accessibilite-numerique'
          )
        })
      )}
    </p>

    <h2 id="securite" class="fr-h5">{m['general.legal.securityTitle']()}</h2>
    <p>{m['general.legal.securityCertif']()}</p>
    <p>{m['general.legal.securityNoMail']()}</p>
    <p>
      <strong>
        {@html sanitize(
          m['general.legal.sources']({
            etalabLinkProps: externalLinkProps(
              'https://www.etalab.gouv.fr/wp-content/uploads/2017/04/ETALAB-Licence-Ouverte-v2.0.pdf'
            ),
            githubLinkProps: externalLinkProps('https://github.com/betagouv/ComparIA')
          })
        )}
      </strong>
    </p>
  </div>
</main>
