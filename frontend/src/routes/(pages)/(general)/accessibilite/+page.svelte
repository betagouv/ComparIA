<script>
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'
</script>

<SeoHead title={m['seo.titles.accessibilite']()} />

<main class="lg:py-15 py-10">
  <div class="fr-container">
    <p>{@html sanitize(m['general.a11y.disclaimer']())}</p>

    <!-- <p>À cette fin, beta.gouv.fr met en œuvre la stratégie et les actions suivantes :</p>
  <ul>
    <li><a href="/accessibilite/schema-pluriannuel">Schéma pluriannuel 2024-2027</a></li>
    <li><a href="/accessibilite/schema-pluriannuel#bilan-2023">Bilan 2023</a></li>
    <li><a href="/accessibilite/schema-pluriannuel#plan-2024">Plan d’action 2024</a></li>
  </ul> -->

    <h1 id="declaration-daccessibilite">{m['general.a11y.title']()}</h1>
    <!-- <p><em>Établie le 24 avril 2024.</em></p> -->
    <p>{@html sanitize(m['general.a11y.desc']())}</p>

    <h2 id="etat-de-conformite">{m['general.a11y.stateTitle']()}</h2>
    <p>{@html sanitize(m['general.a11y.stateDesc']())}</p>
    <ul>
      <li>{m['general.a11y.stateNavigate']()}</li>
      <li>{m['general.a11y.stateScreenReader']()}</li>
      <li>{m['general.a11y.statePrefs']()}</li>
    </ul>

    <!-- <h4 id="défauts-daccessibilité-connus">Défauts d’accessibilité connus</h4>

  <p>Nous souhaitons corriger ces défauts courant 2024 :</p>
  <ul>
    <li>
      Les pages <a href="/stats">Indicateurs</a> et <a href="/communaute/">Communauté</a> affichent des
      graphiques non accessibles.
    </li>
    <li>
      Notre <a href="https://beta.gouv.fr/content/docs/betagouv_presentation.pdf">bilan 2023</a> sous
      forme de PDF n’est pas accessible.
    </li>
  </ul> -->

    <h2 id="amelioration-et-contact">{m['general.a11y.improveTitle']()}</h2>
    <p>{m['general.a11y.improveDesc']()}</p>
    <ul>
      <li>
        {@html sanitize(
          m['general.a11y.improveMail']({
            linkProps: externalLinkProps('mailto:contact@beta.gouv.fr')
          })
        )}
      </li>
      <li>{m['general.a11y.improveAdress']()}</li>
    </ul>
    <p>{m['general.a11y.improveDelay']()}</p>

    <h2 id="voie-de-recours">{m['general.a11y.remedyTitle']()}</h2>
    <p>{m['general.a11y.remedyDesc']()}</p>
    <p>{m['general.a11y.remedyList']()}</p>
    <ul>
      <li>
        {@html sanitize(
          m['general.a11y.remedyAdvocate']({
            linkProps: externalLinkProps('https://formulaire.defenseurdesdroits.fr/')
          })
        )}
      </li>
      <li>
        {@html sanitize(
          m['general.a11y.remedyDelegateAdvocate']({
            linkProps: externalLinkProps('https://www.defenseurdesdroits.fr/saisir/delegues')
          })
        )}
      </li>
      <li>{m['general.a11y.remedyAdvocateAdress']()}</li>
    </ul>
  </div>
</main>
