<script lang="ts">
  import { resolve } from '$app/paths'
  import PrivacyPolicyAdmin from '$components/admin/PrivacyPolicyAdmin.svelte'
  import PageLayout from '$components/PageLayout.svelte'
</script>

<PageLayout
  seoTitle="Politique de confidentialité"
  title="Politique de confidentialité"
  subtitle="Rédigez et publiez l’information relative aux traitements de données personnelles."
>
  <p class="fr-mb-6v">
    <a
      class="fr-link fr-icon-arrow-left-line fr-link--icon-left"
      href={resolve('/admin/legal')}
    >Retour aux documents juridiques</a>
  </p>
  <PrivacyPolicyAdmin standalone />
</PageLayout>
