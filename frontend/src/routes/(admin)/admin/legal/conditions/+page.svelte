<script lang="ts">
  import { resolve } from '$app/paths'
  import TermsDocumentAdmin from '$components/admin/TermsDocumentAdmin.svelte'
  import PageLayout from '$components/PageLayout.svelte'
</script>

<PageLayout
  seoTitle="Conditions d’utilisation"
  title="Conditions d’utilisation"
  subtitle="Rédigez, vérifiez et publiez le document accepté pour participer à l’arène."
>
  <p class="fr-mb-6v">
    <a
      class="fr-link fr-icon-arrow-left-line fr-link--icon-left"
      href={resolve('/admin/legal')}
    >Retour aux documents juridiques</a>
  </p>
  <TermsDocumentAdmin />
</PageLayout>
