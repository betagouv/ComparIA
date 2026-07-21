<script lang="ts">
  import { resolve } from '$app/paths'
  import PageLayout from '$components/PageLayout.svelte'
</script>

<PageLayout
  seoTitle="Documents et parcours juridiques"
  title="Documents et parcours juridiques"
  subtitle="Chaque contenu dispose de son propre espace de gestion et de publication."
>
  <div class="max-w-[900px]">
    <section class="fr-mb-8v" aria-labelledby="participation-journey-group-title">
      <h2 id="participation-journey-group-title" class="fr-h5 fr-mb-2v">Parcours d’acceptation</h2>
      <ul class="fr-raw-list">
        <li class="fr-py-3v">
          <h3 class="fr-h5 fr-mb-1v">
            <a
              class="fr-link fr-icon-arrow-right-line fr-link--icon-right"
              href={resolve('/admin/conditions-participation')}>Parcours de participation</a
            >
          </h3>
          <p class="fr-text--sm fr-mb-0">
            Textes affichés avant le premier message et lors de la connexion.
          </p>
        </li>
      </ul>
    </section>

    <section aria-labelledby="legal-documents-group-title">
      <h2 id="legal-documents-group-title" class="fr-h5 fr-mb-2v">Documents juridiques</h2>
      <ul class="fr-raw-list">
        <li class="fr-py-3v">
          <h3 class="fr-h5 fr-mb-1v">
            <a
              class="fr-link fr-icon-arrow-right-line fr-link--icon-right"
              href={resolve('/admin/legal/conditions')}>Conditions d’utilisation</a
            >
          </h3>
          <p class="fr-text--sm fr-mb-0">Document dont l’acceptation est obligatoire.</p>
          <hr class="fr-hr" />
        </li>
        <li class="fr-py-3v">
          <h3 class="fr-h5 fr-mb-1v">
            <a
              class="fr-link fr-icon-arrow-right-line fr-link--icon-right"
              href={resolve('/admin/legal/confidentialite')}>Politique de confidentialité</a
            >
          </h3>
          <p class="fr-text--sm fr-mb-0">
            Information relative à l’utilisation des données personnelles.
          </p>
        </li>
      </ul>
    </section>
  </div>
</PageLayout>
