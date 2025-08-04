<script>
  import SeoHead from '$lib/components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
</script>

<SeoHead title={m['seo.titles.news']()} />

<section class="fr-container--fluid bg-grey fr-pb-4w fr-pb-md-6w fr-pt-8w">
  <div class="fr-container-md grid-2-md">
    <div class="fr-container">
      <img
        class="fr-my-1w"
        src="/iasummit.png"
        alt="Sommet pour l'action sur l'IA"
        title="Sommet pour l'action sur l'IA"
      />
      <h1>
        Journée compar:<span class="text-purple">IA</span>
      </h1>
      <p class="fr-mr-8w fr-mb-4w">
        Revivez les interventions de notre journée dédiée aux enjeux éthiques, culturels et
        environnementaux des systèmes d'IA conversationnelle.
      </p>
      <button class="purple-btn fr-btn fr-btn--lg cta fr-mb-4w"
        ><a
          href="https://www.youtube.com/playlist?list=PLtRFEzn7EZGIadxkQgxgDdJ0te-U-iRzx"
          class="text-center"
          >Visionner les interventions de la journée
        </a></button
      >
    </div>
    <div class="fr-container">
      <img
        src="/bnf/cover.jpg"
        alt="Conférence d'Anastasia Stasenko dans un amphithéâtre de la BNF, présentant une diapositive qui analyse le jeu de données compar:IA"
        title="Conférence d'Anastasia Stasenko présentant une diapositive qui analyse le jeu de données compar:IA"
        class="rounded-img fr-responsive-img"
      />
    </div>
  </div>
</section>
<section class="bg-blue fr-py-6w">
  <div class="fr-container">
    <h3 class="text-center">Les conférences</h3>
    <div class="grid-2-md">
      <div class="rounded-tile">
        <iframe
          width="560"
          height="315"
          src="https://www.youtube.com/embed/wnKNu_eW7Cc"
          title="YouTube video player"
          frameborder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          referrerpolicy="strict-origin-when-cross-origin"
          allowfullscreen
        ></iframe>
        <h4 class="fr-mt-1w">Ouverture de la journée</h4>
        <p class="text-grey">
          Isabelle Nyffenegger, Thibault Grouas et Lucie Termignon, du Ministère de la Culture
        </p>
      </div>
      <div class="rounded-tile">
        <iframe
          width="560"
          height="315"
          src="https://www.youtube.com/embed/3ayf__MTFzA"
          title="YouTube video player"
          frameborder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          referrerpolicy="strict-origin-when-cross-origin"
          allowfullscreen
        ></iframe>
        <h4 class="fr-mt-1w">Alignement des modèles sur les usages francophones</h4>
        <p class="text-grey">Anastasia Stasenko, de Pleias</p>
      </div>
      <div class="rounded-tile">
        <iframe
          width="560"
          height="315"
          src="https://www.youtube.com/embed/jdALqhnRmCk"
          title="YouTube video player"
          frameborder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          referrerpolicy="strict-origin-when-cross-origin"
          allowfullscreen
        ></iframe>
        <h4 class="fr-mt-1w">Comment rendre l'IA compatible avec la démocratie ?</h4>
        <p class="text-grey">David Mas de Make.org et Benjamin Piwowarski du CNRS.</p>
      </div>
      <div class="rounded-tile">
        <iframe
          width="560"
          height="315"
          src="https://www.youtube.com/embed/i7IAJUzjk0c"
          title="YouTube video player"
          frameborder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          referrerpolicy="strict-origin-when-cross-origin"
          allowfullscreen
        ></iframe>
        <h4 class="fr-mt-1w">L'évaluation de l'impact environnemental des IA génératives</h4>
        <p class="text-grey">Samuel Rincé, de GenAI Impact.</p>
      </div>
      <div class="rounded-tile">
        <iframe
          width="560"
          height="315"
          src="https://www.youtube.com/embed/1oMLenKEhgk"
          title="YouTube video player"
          frameborder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          referrerpolicy="strict-origin-when-cross-origin"
          allowfullscreen
        ></iframe>

        <h4 class="fr-mt-1w">Enjeux d'éducation et de formation à l'IA générative</h4>
        <p class="text-grey">Marie Bancal et Françoise Tort, de Pix.</p>
      </div>
      <div class="rounded-tile">
        <iframe
          width="560"
          height="315"
          src="https://www.youtube.com/embed/kktVcBSkIIY"
          title="YouTube video player"
          frameborder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          referrerpolicy="strict-origin-when-cross-origin"
          allowfullscreen
        ></iframe>
        <h4 class="fr-mt-1w">Vers un futur durable pour l'IA francophone</h4>
        <p class="text-grey">Sasha Luccioni, de Hugging Face.</p>
      </div>
    </div>
  </div>
  <div class="fr-container fr-mt-6w">
    <h3 class="fr-pt-6w text-center">Les ateliers</h3>
    <div class="grid">
      <div class="rounded-tile">
        <span class="text-grey fr-text--sm inline-flex">
          <svg
            class="fr-mr-1v"
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M10.0013 18.3333C5.39893 18.3333 1.66797 14.6023 1.66797 9.99996C1.66797 5.39758 5.39893 1.66663 10.0013 1.66663C14.6036 1.66663 18.3346 5.39758 18.3346 9.99996C18.3346 14.6023 14.6036 18.3333 10.0013 18.3333ZM10.0013 16.6666C13.6832 16.6666 16.668 13.6819 16.668 9.99996C16.668 6.31806 13.6832 3.33329 10.0013 3.33329C6.3194 3.33329 3.33464 6.31806 3.33464 9.99996C3.33464 13.6819 6.3194 16.6666 10.0013 16.6666ZM10.8346 9.99996H14.168V11.6666H9.16797V5.83329H10.8346V9.99996Z"
              fill="#7F7F7F"
            />
          </svg>
          11h à 11h45
        </span>
        <span class="fr-badge fr-badge--sm fr-badge--yellow-tournesol">Atelier</span>
        <h6>La bataille de l’IA</h6>
        <p class="text-grey fr-text--sm text-left">Margaux Levisalles de Latitudes</p>
      </div>

      <div class="rounded-tile">
        <span class="text-grey fr-text--sm inline-flex">
          <svg
            class="fr-mr-1v"
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M10.0013 18.3333C5.39893 18.3333 1.66797 14.6023 1.66797 9.99996C1.66797 5.39758 5.39893 1.66663 10.0013 1.66663C14.6036 1.66663 18.3346 5.39758 18.3346 9.99996C18.3346 14.6023 14.6036 18.3333 10.0013 18.3333ZM10.0013 16.6666C13.6832 16.6666 16.668 13.6819 16.668 9.99996C16.668 6.31806 13.6832 3.33329 10.0013 3.33329C6.3194 3.33329 3.33464 6.31806 3.33464 9.99996C3.33464 13.6819 6.3194 16.6666 10.0013 16.6666ZM10.8346 9.99996H14.168V11.6666H9.16797V5.83329H10.8346V9.99996Z"
              fill="#7F7F7F"
            />
          </svg>
          13h à 13h45
        </span>
        <span class="fr-badge fr-badge--sm fr-badge--yellow-tournesol">Atelier</span>
        <h6>La boîte noire de l’IA</h6>
        <p class="text-grey fr-text--sm text-left">Loup Cellard de Datactivist</p>
      </div>

      <div class="rounded-tile">
        <span class="text-grey fr-text--sm inline-flex">
          <svg
            class="fr-mr-1v"
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M10.0013 18.3333C5.39893 18.3333 1.66797 14.6023 1.66797 9.99996C1.66797 5.39758 5.39893 1.66663 10.0013 1.66663C14.6036 1.66663 18.3346 5.39758 18.3346 9.99996C18.3346 14.6023 14.6036 18.3333 10.0013 18.3333ZM10.0013 16.6666C13.6832 16.6666 16.668 13.6819 16.668 9.99996C16.668 6.31806 13.6832 3.33329 10.0013 3.33329C6.3194 3.33329 3.33464 6.31806 3.33464 9.99996C3.33464 13.6819 6.3194 16.6666 10.0013 16.6666ZM10.8346 9.99996H14.168V11.6666H9.16797V5.83329H10.8346V9.99996Z"
              fill="#7F7F7F"
            />
          </svg>
          14h à 14h45
        </span>
        <span class="fr-badge fr-badge--sm fr-badge--yellow-tournesol">Atelier</span>
        <h6>Les modules apprenants Modulix</h6>
        <p class="text-grey fr-text--sm text-left">Romain Pennec de PIX</p>
      </div>

      <div class="rounded-tile">
        <span class="text-grey fr-text--sm inline-flex">
          <svg
            class="fr-mr-1v"
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M10.0013 18.3333C5.39893 18.3333 1.66797 14.6023 1.66797 9.99996C1.66797 5.39758 5.39893 1.66663 10.0013 1.66663C14.6036 1.66663 18.3346 5.39758 18.3346 9.99996C18.3346 14.6023 14.6036 18.3333 10.0013 18.3333ZM10.0013 16.6666C13.6832 16.6666 16.668 13.6819 16.668 9.99996C16.668 6.31806 13.6832 3.33329 10.0013 3.33329C6.3194 3.33329 3.33464 6.31806 3.33464 9.99996C3.33464 13.6819 6.3194 16.6666 10.0013 16.6666ZM10.8346 9.99996H14.168V11.6666H9.16797V5.83329H10.8346V9.99996Z"
              fill="#7F7F7F"
            />
          </svg>
          15h à 15h45
        </span>
        <span class="fr-badge fr-badge--sm fr-badge--yellow-tournesol">Atelier</span>
        <h6>Atelier Café IA : dialogue constructif sur l'IA</h6>
        <p class="text-grey fr-text--sm text-left">Jean Cattan du Conseil national du numérique</p>
      </div>

      <div class="rounded-tile">
        <span class="text-grey fr-text--sm inline-flex">
          <svg
            class="fr-mr-1v"
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M10.0013 18.3333C5.39893 18.3333 1.66797 14.6023 1.66797 9.99996C1.66797 5.39758 5.39893 1.66663 10.0013 1.66663C14.6036 1.66663 18.3346 5.39758 18.3346 9.99996C18.3346 14.6023 14.6036 18.3333 10.0013 18.3333ZM10.0013 16.6666C13.6832 16.6666 16.668 13.6819 16.668 9.99996C16.668 6.31806 13.6832 3.33329 10.0013 3.33329C6.3194 3.33329 3.33464 6.31806 3.33464 9.99996C3.33464 13.6819 6.3194 16.6666 10.0013 16.6666ZM10.8346 9.99996H14.168V11.6666H9.16797V5.83329H10.8346V9.99996Z"
              fill="#7F7F7F"
            />
          </svg>
          15h45 à 16h30
        </span>
        <span class="fr-badge fr-badge--sm fr-badge--yellow-tournesol">Atelier</span>
        <h6>
          Retour sur la consultation citoyenne “Quelles sont vos idées pour mettre l’IA au service
          de l’intérêt général ?"
        </h6>
        <p class="text-grey fr-text--sm text-left">Victor Laymand de Make.org</p>
      </div>
    </div>
  </div>
</section>
<section class="fr-py-6w">
  <h3 class="text-center">Les intervenant·es</h3>
  <div class="fr-container portraits">
    <div class="w-min">
      <div class="rounded-tile bg-blue">
        <div>
          <img class="rounded-img" src="/bnf/marie-bancal.jpg" width="226" height="226" />
          <h6 class="fr-pt-3w fr-mb-1w">Marie Bancal</h6>
          <p class="text-grey text-left">Directrice adjointe de Pix</p>
        </div>
        <img src="/orgs/pix.svg" width="100" alt="Pix" title="Pix" />
      </div>
      <div class="rounded-tile bg-blue">
        <div>
          <img class="rounded-img" src="/bnf/mathilde-bras.jpg" width="226" height="226" />
          <h6 class="fr-pt-3w fr-mb-1w">Mathilde Bras</h6>
          <p class="text-grey text-left">Co-Responsable de l'Atelier numérique</p>
        </div>
        <div>
          <img class="fr-mr-1w dark-invert" src="/orgs/ateliernumerique.png" width="100" />
          <img src="/orgs/minicult.svg" width="110" />
        </div>
      </div>
      <div class="rounded-tile bg-blue">
        <div>
          <img
            class="rounded-img"
            src="/bnf/margaux-levisalles.jpg"
            width="226"
            height="226"
          />
          <h6 class="fr-pt-3w fr-mb-1w">Margaux Levisalles</h6>
          <p class="text-grey text-left">Co-fondatrice de Latitudes</p>
        </div>
        <img
          class="dark-invert"
          src="/orgs/latitudes.png"
          alt="Latitudes"
          title="Latitudes"
          width="150"
        />
      </div>
      <div class="rounded-tile bg-blue">
        <div>
          <img class="rounded-img" src="/bnf/jean-cattan.jpg" width="226" height="226" />
          <h6 class="fr-pt-3w fr-mb-1w">Jean Cattan</h6>
          <p class="text-grey text-left">Secrétaire général du Conseil national du numérique</p>
        </div>
        <img src="/orgs/cnnum.png" class="dark-invert" width="100" />
      </div>
      <div class="rounded-tile bg-blue">
        <div>
          <img class="rounded-img" src="/bnf/loup-cellard.jpg" width="226" height="226" />
          <h6 class="fr-pt-3w fr-mb-1w">Loup Cellard</h6>
          <p class="text-grey text-left">Chercheur chez Datactivist</p>
        </div>
        <div>
          <img src="/orgs/datactivist.png" width="150" class="fr-mr-1w dark-invert" />
        </div>
      </div>
      <div class="rounded-tile bg-blue">
        <div>
          <img class="rounded-img" src="/bnf/romain-delassus.jpg" width="226" height="226" />
          <h6 class="fr-pt-3w fr-mb-1w">Romain Delassus</h6>
          <p class="text-grey text-left">Chef du service du numérique du Ministère de la Culture</p>
        </div>
        <img
          src="/orgs/minicult.svg"
          width="110"
          alt="Ministère de la Culture"
          title="Ministère de la Culture"
        />
      </div>

      <div class="rounded-tile bg-blue">
        <div>
          <img class="rounded-img" src="/bnf/victor-laymand.jpg" width="226" height="226" />
          <h6 class="fr-pt-3w fr-mb-1w">Victor Laymand</h6>
          <p class="text-grey text-left">Directeur des études chez make.org</p>
        </div>
        <img src="/orgs/make-org.svg" alt="Make.org" title="Make.org" width="100" />
      </div>
      <div class="rounded-tile bg-blue">
        <div>
          <img class="rounded-img" src="/bnf/sasha-luccioni.jpg" width="226" height="226" />
          <h6 class="fr-pt-3w fr-mb-1w">Sasha Luccioni</h6>
          <p class="text-grey text-left">AI &amp; Climate Lead chez Hugging Face</p>
        </div>
        <img
          src="/orgs/huggingface-full.svg"
          width="160"
          alt="Hugging Face"
          title="Hugging Face"
        />
      </div>
      <div class="rounded-tile bg-blue">
        <div>
          <img class="rounded-img" src="/bnf/david-mas.jpg" width="226" height="226" />
          <h6 class="fr-pt-3w fr-mb-1w">David Mas</h6>
          <p class="text-grey text-left">Chief AI Officer chez Make.org</p>
          <!-- <img src="/orgs/communs-democratiques.svg" alt="Consortium Communs Démocratiques" title="Consortium Communs Démocratiques width="100"> -->
        </div>
        <img src="/orgs/make-org.svg" alt="Make.org" title="Make.org" width="100" />
      </div>
      <div class="rounded-tile bg-blue">
        <div>
          <img
            class="rounded-img"
            src="/bnf/benjamin-piwowarski.jpg"
            width="226"
            height="226"
          />
          <h6 class="fr-pt-3w fr-mb-1w">Benjamin Piwowarski</h6>
          <p class="text-grey text-left">Directeur de recherche au CNRS</p>
          <!-- <img src="/orgs/communs-democratiques.svg" alt="Consortium Communs Démocratiques" title="Consortium Communs Démocratiques width="100"> -->
        </div>
        <img class="dark-invert" src="/orgs/cnrs.svg" alt="CNRS" title="CNRS" width="110" />
      </div>
      <div class="rounded-tile bg-blue">
        <div>
          <img class="rounded-img" src="/bnf/samuel-rince.jpg" width="226" height="226" />
          <h6 class="fr-pt-3w fr-mb-1w">Samuel Rincé</h6>
          <p class="text-grey text-left">Président et cofondateur de GenAI Impact</p>
        </div>
        <img class="dark-invert" src="/orgs/genai.png" width="130" />
      </div>
      <div class="rounded-tile bg-blue">
        <div>
          <img
            class="rounded-img"
            src="/bnf/anastasia-stasenko.jpg"
            width="226"
            height="226"
          />
          <h6 class="fr-pt-3w fr-mb-1w">Anastasia Stasenko</h6>
          <p class="text-grey text-left">Cofondatrice de Pleias</p>
        </div>
        <img class="dark-invert" src="/orgs/pleias.png" width="130" />
      </div>
      <div class="rounded-tile bg-blue">
        <div>
          <img class="rounded-img" src="/bnf/lucie-termignon.jpg" width="226" height="226" />
          <h6 class="fr-pt-3w fr-mb-1w">Lucie Termignon</h6>
          <p class="text-grey text-left">Cheffe de produit de compar:IA</p>
        </div>
        <div>
          <img src="/orgs/comparia.svg" width="80" class="fr-mr-1w" />
          <img
            src="/orgs/minicult.svg"
            width="110"
            alt="Ministère de la Culture"
            title="Ministère de la Culture"
          />
        </div>
      </div>
      <div class="rounded-tile bg-blue">
        <div>
          <img class="rounded-img" src="/bnf/francoise-tort.jpg" width="226" height="226" />
          <h6 class="fr-pt-3w fr-mb-1w">Françoise Tort</h6>
          <p class="text-grey text-left">Conceptrice de défis pédagogiques chez Pix</p>
        </div>
        <img src="/orgs/pix.svg" width="100" alt="Pix" title="Pix" />
      </div>
    </div>
  </div>
</section>
<section class="bg-blue fr-grid-row fr-grid-row--center">
  <div class="fr-col-12 fr-col-md-6">
    <h4 class="fr-pt-6w text-center">À propos de la journée compar:IA</h4>
    <p class="text-center">
      La journée compar:IA s'est tenue le 7 février 2025 à la Bnf François-Mitterrand. L'évènement a
      réuni plus de 300 participant·es en présentiel et une centaine de personnes ont suivi la
      journée en direct.
    </p>
    <p class="text-center">
      L'objectif était d'échanger sur les enjeux éthiques, culturels et environnementaux liés à l'IA
      conversationnelle.
    </p>
    <p class="fr-pb-4w text-center">
      Un grand merci à tou·tes les participant·es et aux partenaires de l'évènement !
    </p>
  </div>
  <div class="fr-grid-row fr-grid-row--center fr-grid-row--middle fr-grid-row--gutters fr-mb-4w">
    <div class="fr-col-md-2 fr-col-6">
      <img
        class=""
        src="/orgs/minicult.svg"
        alt="Ministère de la Culture"
        title="Ministère de la Culture"
        width="137px"
        height="97px"
      />
    </div>
    <div class="fr-col-md-2 fr-col-6">
      <img
        class="dark-invert"
        src="/orgs/ateliernumerique.png"
        alt="Atelier numérique"
        title="Atelier numérique"
        width=""
        height="105px"
      />
    </div>

    <div class="fr-col-md-2 fr-col-6">
      <img
        src="/iasummit.png"
        alt="Sommet de l'IA"
        title="Sommet pour l'action sur l'IA"
        class="dark-invert fr-responsive-img"
        width=""
        height=""
      />
    </div>
    <div class="fr-col-md-2 fr-col-6">
      <img
        src="/orgs/betagouv.svg"
        alt="beta.gouv.fr"
        title="beta.gouv.fr"
        class="dark-invert fr-responsive-img"
        height="65px"
      />
    </div>
    <div class="fr-col-md-1 fr-col-6">
      <img
        src="/orgs/bnf.svg"
        class="dark-invert fr-responsive-img"
        alt="BNF"
        title="BNF"
        width=""
        height=""
      />
    </div>
  </div>
</section>

<style>
  @media (prefers-color-scheme: dark) {
    * {
      color: white !important;
    }
  }

  .temp-banner {
    display: none !important;
  }

  .flex {
    display: flex;
  }

  .inline-block {
    display: inline-block;
  }

  .text-purple {
    color: var(--blue-france-main-525);
  }

  .rounded-tile {
    border-color: #e5e5e5;
    border-width: 1.5px;
    border-style: solid;
    border-radius: 1rem;
    padding: 1em;
  }

  .rounded-tile.bg-blue {
    background-color: #f3f5f9 !important;
  }

  .portraits .rounded-tile {
    justify-content: space-between;
    display: grid;
  }

  .bg-blue {
    /* background-color: var(--blue-france-975-75); */
    /* --background-contrast-info: var(--info-950-100); */
    /* background-color: var(--background-contrast-info); */
    background-color: #f3f5f9;
  }

  .bg-light-blue {
    /* --blue-france-main-525: #6A6AF4; */
    --blue-france-main-525-hover: #9898f8;
    --blue-france-main-525-active: #aeaef9;
    --hover: var(--blue-france-main-525-hover);
    --active: var(--blue-france-main-525-active);
    background-color: var(--blue-france-main-525);
  }

  @media (prefers-color-scheme: dark) {
    .bg-blue {
      background-color: #1c1e22 !important;
    }

    .bg-grey {
      background-color: #0a0a0b !important;
    }

    .rounded-tile {
      background-color: black !important;
    }

    .rounded-tile.bg-blue {
      background-color: #1c1e22 !important;
    }

    .dark-invert {
      filter: invert(1);
    }

    .text-grey {
      color: var(--grey-200-850) !important;
    }
  }

  @media (prefers-color-scheme: light) {
    .bg-light-grey {
      background-color: #fcfcfd;
    }

    .rounded-tile {
      background-color: white;
    }

    #formItem-mbtext-email.fr-input {
      background-color: white;
    }
  }

  .fr-badge {
    float: right;
  }

  .fr-header__service-title .fr-badge {
    float: unset;
  }

  .grid {
    display: grid;
    gap: 1.5em;
    grid-template-columns: 1fr;
  }

  .grid .rounded-tile {
    padding: 1.5em;
  }

  .grid-4 {
    display: grid;
    gap: 1.5em;
    grid-template-columns: 1fr 1fr;
  }

  .grid-4 .rounded-tile {
    padding: 1.5em;
  }

  .grid-2-md {
    display: grid;
    grid-template-columns: 1fr;
    gap: 2em;
  }

  ul {
    font-size: 14px;
    color: #747474;
  }

  .cta {
    width: 100%;
  }

  h5 {
    font-size: 18px;
  }

  @media (min-width: 62em) {
    .cta {
      width: 80%;
    }

    .grid {
      grid-template-columns: 1fr 1fr 1fr;
    }

    .grid-4 {
      grid-template-columns: 1fr 1fr 1fr 1fr;
    }

    .grid-2-md {
      grid-auto-rows: 1fr;
      grid-template-columns: 1fr 1fr;
    }
  }

  .align-center {
    align-items: center;
  }

  .h-full {
    height: 100%;
  }

  .cadre p,
  .cadre {
    font-size: 9px !important;
  }

  .cadre {
    border-style: solid;
    border-color: var(--border-default-grey) !important;
    border-width: 0.5px;
    padding: 1em;
  }

  .cadre .texte::before {
    content: 'Réponse modèle B';
    text-transform: uppercase;
    color: var(--text-label-green-tilleul-verveine);
    padding: 2px 4px;
    background-color: var(--background-contrast-green-tilleul-verveine);
    --idle: transparent;
    --hover: var(--background-contrast-green-tilleul-verveine-hover);
    --active: var(--background-contrast-green-tilleul-verveine-active);
    font-weight: 700;
  }

  legend {
    color: var(--text-mention-grey);
  }

  h6 {
    font-size: 1.1em;
    color: #3a3a3a;
    margin-bottom: 0.5em;
  }

  p {
    text-align: justify;
  }

  strong {
    font-weight: 500;
  }

  .cta a {
    margin: auto;
  }

  .fr-badge--purple {
    background-color: #6a6af4;
    color: #fff;
  }

  .fr-badge--corail {
    color: #fff;
    background-color: #ff9575;
  }

  .w-min {
    display: flex;
    flex-wrap: wrap;
    gap: 2em;
  }

  .w-min .rounded-tile {
    width: min-content;
  }

  .bg-grey {
    background-color: #fcfcfd;
  }

  .spaced {
    line-height: 2.4em;
  }

  .text-left {
    text-align: left;
  }

  .rounded-img {
    border-radius: 8px;
  }

  .fr-badge--yellow-tournesol {
    color: var(--text-label-yellow-tournesol) !important;
  }

  .inline-flex {
    display: inline-flex;
    margin-bottom: 1em;
    align-content: center;
  }
</style>
