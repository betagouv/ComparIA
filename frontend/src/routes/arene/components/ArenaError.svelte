<script lang="ts">
  import { Icon, Link } from '$components/dsfr'

  export let reconnectAttempts: number = 0
  export let onRetry: () => void = () => {}

  const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000)
</script>

<div class="fr-container">
  <div
    class="fr-my-7w fr-mt-md-12w fr-mb-md-10w fr-grid-row fr-grid-row--gutters fr-grid-row--middle fr-grid-row--center"
  >
    <div class="fr-py-0 fr-col-12 fr-col-md-6">
      <h1>Service temporairement indisponible</h1>
      <p class="fr-text--sm fr-mb-3w">Erreur 503</p>
      <p class="fr-text--sm fr-mb-5w">
        Désolé, l'arène rencontre un problème technique, nous travaillons pour le résoudre le plus
        rapidement possible.
      </p>
      <p class="fr-text--lead fr-mb-3w">
        Tentative de reconnexion dans {delay / 1000} secondes...
      </p>
      <ul class="fr-btns-group fr-btns-group--inline-md">
        <li>
          <button class="fr-btn fr-btn--secondary" on:click={onRetry}>
            Réessayer maintenant
          </button>
        </li>
        <li>
          <Link
            button
            variant="secondary"
            href="/"
            text="Retour à l'accueil"
            class="w-full! md:w-auto!"
          />
        </li>
      </ul>
    </div>
    <div class="fr-col-12 fr-col-md-3 fr-col-offset-md-1 fr-px-6w fr-px-md-0 fr-py-0">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="fr-responsive-img fr-artwork"
        aria-hidden="true"
        width="160"
        height="200"
        viewBox="0 0 160 200"
      >
        <use class="fr-artwork-motif" href="/static/dsfr/artwork/system.svg#artwork-motif"></use>
        <use class="fr-artwork-background" href="/static/dsfr/artwork/system.svg#artwork-background"
        ></use>
        <g transform="translate(40, 60)">
          <use
            class="fr-artwork-decorative"
            href="/static/dsfr/artwork/system.svg#artwork-decorative"
          ></use>
          <use class="fr-artwork-minor" href="/static/dsfr/artwork/system.svg#artwork-minor"></use>
          <use class="fr-artwork-major" href="/static/dsfr/artwork/system.svg#artwork-major"></use>
        </g>
      </svg>
    </div>
  </div>
</div>
