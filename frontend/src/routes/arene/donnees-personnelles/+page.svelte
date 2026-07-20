<script lang="ts">
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import SeoHead from '$components/SEOHead.svelte'
  import { api } from '$lib/fastapi-client'
  import { getI18nContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  const i18nData = getI18nContext()
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
      <p class="fr-text--lead">
        compar:IA traite des données à caractère personnel pour fournir le service, sécuriser les
        accès et permettre la comparaison des modèles d’IA. La participation à l’arène comprend
        l’évaluation des modèles ainsi que la réutilisation des conversations et votes pour la
        recherche et la production de jeux de données, conformément aux conditions d’utilisation.
      </p>

      <div class="fr-alert fr-alert--info mb-8" role="note">
        <h2 class="fr-alert__title">Avant d’écrire un message</h2>
        <p>
          Ne saisissez pas d’information sensible ou permettant de vous identifier ou d’identifier
          une autre personne. Les messages sont transmis aux fournisseurs des modèles sélectionnés.
        </p>
      </div>

      <h2 id="responsable">Responsable du traitement</h2>
      <p>
        Le service du numérique du ministère de la Culture est responsable des traitements mis en
        œuvre par compar:IA. Vous pouvez contacter l’équipe à
        <a href="mailto:{i18nData.contact}">{i18nData.contact}</a>.
      </p>

      <h2 id="donnees">Données traitées</h2>
      <ul>
        <li>
          conversations et comparaisons : messages, réponses des modèles, votes, signalements et
          métadonnées de comparaison ;
        </li>
        <li>
          compte et sécurité : adresse électronique, codes de connexion, sessions, adresse IP,
          navigateur et journaux techniques ;
        </li>
        <li>
          mesure d’audience, si vous l’autorisez : pages consultées et informations techniques
          limitées ;
        </li>
        <li>formulaires facultatifs : informations saisies dans les formulaires Tally.</li>
      </ul>

      <h2 id="finalites">Finalités et bases juridiques</h2>
      <div class="fr-table fr-table--bordered">
        <table>
          <caption>Pourquoi les données sont utilisées</caption>
          <thead>
            <tr><th scope="col">Finalité</th><th scope="col">Fondement présenté</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>Fournir la comparaison, gérer le compte et sécuriser le service</td>
              <td>Exécution des conditions d’utilisation et mission d’intérêt public</td>
            </tr>
            <tr>
              <td>Réutiliser conversations et votes pour la recherche ou des jeux de données</td>
              <td
                >Participation à l’arène selon les conditions d’utilisation et mission d’intérêt
                public</td
              >
            </tr>
            <tr>
              <td>Mesurer l’audience</td>
              <td>Votre choix explicite sur cet appareil</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p>
        La qualification juridique définitive de chaque traitement et l’éventuelle mission d’intérêt
        public doivent être confirmées dans le registre du responsable de traitement.
      </p>

      <h2 id="destinataires">Destinataires et sous-traitants</h2>
      <p>Selon la fonctionnalité utilisée, les données peuvent être accessibles :</p>
      <ul>
        <li>aux agents habilités du ministère de la Culture et à l’hébergeur OVHcloud ;</li>
        <li>aux fournisseurs des modèles d’IA et au service de modération sélectionnés ;</li>
        <li>à Linkup lors de l’utilisation de la recherche web ;</li>
        <li>
          à Sentry pour le diagnostic technique, avec des données qui doivent être minimisées ;
        </li>
        <li>à Matomo uniquement si vous autorisez la mesure d’audience ;</li>
        <li>à Tally lorsque vous envoyez volontairement un formulaire ;</li>
        <li>
          aux personnes autorisées à accéder aux jeux de données publiés sur Hugging Face,
          uniquement pour les conversations produites dans le cadre de la participation à l’arène.
        </li>
      </ul>
      <p>
        Certains fournisseurs peuvent traiter des données hors de l’Espace économique européen. La
        liste à jour des fournisseurs, leur pays et les garanties de transfert doivent être publiée
        avant leur utilisation.
      </p>

      <h2 id="conservation">Durées de conservation</h2>
      <p>
        Les sessions de connexion expirent après 30 jours. Les durées applicables aux comptes,
        journaux, conversations, consentements et exports doivent encore être fixées et publiées par
        le responsable de traitement, puis appliquées par une suppression automatique. Vous pouvez
        demander dès maintenant la suppression des données vous concernant.
      </p>

      <h2 id="droits">Vos droits</h2>
      <p>
        Vous pouvez demander l’accès, la rectification, l’effacement ou la portabilité de vos
        données, limiter leur traitement, vous y opposer lorsque ce droit s’applique et retirer un
        accord sans remettre en cause les traitements antérieurs. Écrivez à
        <a href="mailto:{i18nData.contact}">{i18nData.contact}</a>. Vous pouvez également adresser
        une réclamation à la <a href="https://www.cnil.fr/fr/plaintes" rel="external">CNIL</a>.
      </p>
    {/if}

    {#if !loading && !privacyPolicy}
      <h2 id="publication">Publication des conversations</h2>
      <p>
        Les conversations et votes produits dans l’arène peuvent contribuer à l’évaluation, à la
        recherche et à des jeux de données selon les conditions d’utilisation. Les contrôles
        automatiques de données personnelles réduisent le risque mais ne garantissent pas, à eux
        seuls, une anonymisation irréversible. Ne saisissez donc aucune donnée sensible ou
        directement identifiante.
      </p>

      <p class="fr-text--sm text-grey">
        Cette page doit être complétée avec les durées définitives, la liste contractuelle des
        fournisseurs, les garanties de transfert et les coordonnées du délégué à la protection des
        données après validation par le ministère.
      </p>
    {/if}
  </div>
</main>
