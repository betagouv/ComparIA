<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
</script>

<div class="mt-3 text-center">
  <div class="bg-light-info p-3 inline-block">
    <Link href="#" text="Haut de page" icon="arrow-up-line" class="pb-1!" />
  </div>
</div>
<section class="fr-container--fluid bg-light-info">
  <div class="fr-container pb-10 pt-8">
    <div class="mb-4">
      <h5 class="mb-2! flex items-center">
        <Icon icon="i-ri-mail-line" size="lg" block class="text-primary me-2" />
        Abonnez-vous à notre lettre d'information
      </h5>
      <p class="text-sm!">
        Retrouvez les dernières actualités du projet : partenariats, intégration de nouveaux
        modèles, publications de jeux de données et nouvelles fonctionnalités !
      </p>
    </div>
    <div>
      <iframe
        data-tally-src="https://tally.so/embed/zxKR40?alignLeft=1&hideTitle=1&transparentBackground=1&dynamicHeight=1"
        loading="lazy"
        width="100%"
        height="380"
        frameborder="0"
        marginheight="0"
        marginwidth="0"
        title="Infolettre CompaRAG"
        class="outline-none! dark:invert"
      ></iframe>
    </div>
  </div>
</section>

<style>
  iframe {
    color-scheme: light;
  }
</style>
