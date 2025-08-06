<script>
  import { m } from '$lib/i18n/messages'
</script>

<div class="fr-container">
  <div class="fr-container bg-blue fr-my-4w fr-py-4w">
    <h3>Partenaires institutionnels</h3>
    <div class="fr-grid-row fr-grid-row--center fr-grid-row--middle">
      <div class="fr-mx-2w">
        <img
          src="/orgs/cnnum.png"
          alt="Conseil national du numérique"
          width="112px"
          height="55px"
          title="Conseil national du numérique"
        />
      </div>

      <div class="fr-mx-2w">
        <img src="/orgs/etalab.svg" alt="Etalab" width="200px" height="43px" title="Etalab" />
      </div>
      <div class="fr-mx-2w">
        <img
          src="/orgs/peren.svg"
          alt="PEReN, Pôle d'expertise de la régulation numérique"
          width="270px"
          height=""
          title="Pôle d'expertise de la régulation numérique (PEReN)"
        />
      </div>
    </div>
  </div>
  <div class="fr-container bg-yellow fr-my-4w fr-py-4w">
    <h3>Partenaires de diffusion</h3>
    <p>
      Nous créons un réseau de partenaires intégrant le comparateur dans leur offre de services et
      de formation.
    </p>
    <div class="fr-grid-row fr-grid-row--center fr-grid-row--middle">
      <div class="">
        <img
          src="/orgs/cafe-ia.png"
          alt="Cafés de l'IA"
          width="205px"
          height="132px"
          title="Cafés IA"
        />
      </div>

      <div class="fr-mr-2w">
        <img
          src="/orgs/latitudes.png"
          class="dark-invert"
          alt="Latitudes"
          width="200px"
          height="47px"
          title="Latitudes"
        />
      </div>
      <div class="fr-mx-2w">
        <img src="/orgs/pix.svg" alt="Pix" width="90px" height="75px" title="Pix" />
      </div>
      <div class="fr-mx-2w">
        <img
          src="/orgs/fresque-de-lia.png"
          alt="Fresques de l'IA"
          width="200px"
          height="200px"
          class="dark-invert"
          title="Fresques de l'IA"
        />
      </div>
    </div>
    <p class="fr-mt-4w text-center">
      <strong>Vous souhaitez utiliser le comparateur pour répondre à un besoin métier ?</strong>
    </p>
    <p class="text-center">
      <a
        href="mailto:contact@comparia.beta.gouv.fr"
        class="fr-btn"
        rel="noopener external"
        target="_blank">Dites-nous en plus</a
      >
    </p>
  </div>
  <div class="fr-container bg-grey fr-my-4w fr-py-4w">
    <h3>Partenaires académiques</h3>
    <p>
      Nous avons à coeur que les jeux de données générés alimentent des travaux de recherche
      multidisciplinaires mêlant sciences humaines et sociales et data science.
    </p>
    <div class="text-center">
      <img src="/orgs/inria.png" alt="Inria" width="166px" height="63px" title="Inria" />
    </div>
    <p class="fr-mt-4w text-center">
      <strong
        >Vous menez un projet de recherche et avez des suggestions ou besoin de précision sur la
        démarche et/ou les jeux de données produits ?</strong
      >
    </p>
    <p class="text-center">
      <a
        href="mailto:contact@comparia.beta.gouv.fr"
        class="fr-btn"
        rel="noopener external"
        target="_blank">Contactez-nous</a
      >
    </p>
  </div>
  <div class="fr-container bg-green fr-my-4w fr-py-4w">
    <h3>Services mis à contribution</h3>
    <p>Les calculs d’impacts environnementaux reposent sur les produits ci dessous.</p>

    <div class="fr-grid-row fr-grid-row--center fr-grid-row--middle">
      <div class="fr-mx-2w">
        <img
          src="/orgs/genai.png"
          alt="Gen AI Impact"
          width="110px"
          height="67px"
          title="Gen AI Impact"
        />
      </div>
      <div class="fr-mx-2w">
        <img
          src="/orgs/impactco2.png"
          alt="Impact CO2"
          width="123px"
          height="50px"
          title="Impact CO2"
        />
      </div>
    </div>
  </div>
</div>

<style>
  .bg-blue {
    /* --background-contrast-info: var(--info-950-100); */
    background-color: var(--blue-france-975-75);
  }

  .bg-yellow {
    background-color: var(--yellow-tournesol-975-75);
  }

  .bg-green {
    background-color: var(--green-emeraude-975-75);
  }

  .bg-grey {
    background-color: var(--background-alt-grey);
  }

  .text-blue,
  h3 {
    color: var(--text-action-high-blue-france);
    /* --text-action-high-blue-france: var(--blue-france-sun-113-625); */

    /* color: var(--text-action-high-blue-france) !important; */
  }

  @media (prefers-color-scheme: dark) {
    .dark-invert {
      filter: invert(1);
    }
  }
</style>
