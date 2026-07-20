<script lang="ts">
  import { resolve } from '$app/paths'
  import PageLayout from '$components/PageLayout.svelte'
</script>

<PageLayout
  seoTitle="Documents et parcours juridiques"
  title="Documents et parcours juridiques"
  subtitle="Chaque contenu dispose de son propre espace de gestion et de publication."
>
  <div class="fr-grid-row fr-grid-row--gutters max-w-[1100px]">
    <div class="fr-col-12 fr-col-lg-4">
      <article class="fr-card fr-card--shadow h-full">
        <div class="fr-card__body">
          <div class="fr-card__content">
            <h2 class="fr-card__title">
              <a href={resolve('/admin/conditions-participation')}>Parcours de participation</a>
            </h2>
            <p class="fr-card__desc">
              Fenêtre du premier message, case de connexion et textes présentés avant l’acceptation.
            </p>
            <p class="fr-card__detail">Configuration modifiable</p>
          </div>
        </div>
      </article>
    </div>

    <div class="fr-col-12 fr-col-lg-4">
      <article class="fr-card fr-card--shadow h-full">
        <div class="fr-card__body">
          <div class="fr-card__content">
            <h2 class="fr-card__title">
              <a href={resolve('/admin/legal/conditions')}>Conditions d’utilisation</a>
            </h2>
            <p class="fr-card__desc">
              Document accepté pour participer à l’arène, avec versions et historique immuable.
            </p>
            <p class="fr-card__detail">Document versionné</p>
          </div>
        </div>
      </article>
    </div>

    <div class="fr-col-12 fr-col-lg-4">
      <article class="fr-card fr-card--shadow h-full">
        <div class="fr-card__body">
          <div class="fr-card__content">
            <h2 class="fr-card__title">
              <a href={resolve('/admin/legal/confidentialite')}>Politique de confidentialité</a>
            </h2>
            <p class="fr-card__desc">
              Information sur les traitements de données, publiée indépendamment des conditions.
            </p>
            <p class="fr-card__detail">Document versionné</p>
          </div>
        </div>
      </article>
    </div>
  </div>

  <div class="fr-callout fr-mt-8v max-w-[1100px]">
    <h2 class="fr-callout__title">Comment ces contenus s’articulent-ils ?</h2>
    <p class="fr-callout__text">
      Le parcours affiche les textes courts et renvoie vers les deux documents. Modifier la
      politique de confidentialité ou le parcours ne force pas une nouvelle acceptation des
      conditions. Seules les conditions d’utilisation suivent un cycle de publication lié à leur
      acceptation.
    </p>
  </div>
</PageLayout>
