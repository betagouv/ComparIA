<script lang="ts">
  import Snackbar from '$lib/components/Snackbar.svelte'
  async function handleNewsletterSubmit(event) {
    event.preventDefault() // Prevent the default form submission
    const form = event.target
    const formData = new FormData(form)
    try {
      const response = await fetch(form.action, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams(formData).toString()
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const responseText = await response.text()
      const parser = new DOMParser()
      const doc = parser.parseFromString(responseText, 'text/html')
      const completedDiv = doc.querySelector('.formCompleted')

      if (completedDiv) {
        showSnackbar('Merci, votre inscription à la newsletter a été prise en compte.')
      } else {
        showSnackbar("Erreur lors de l'inscription à la newsletter.")
      }
    } catch (error) {
      console.error('Newsletter subscription error:', error)
      showSnackbar("Echec de l'inscription.")
    }
  }
</script>

<div class="fr-mt-4w fr-pb-1w text-center">
  <span class="bg-very-light-grey fr-py-1w fr-px-3v">
    <a class="fr-link fr-icon-arrow-up-line fr-link--icon-left fr-pb-1v" href="#top">
      Haut de page
    </a>
  </span>
</div>
<section class="fr-container--fluid bg-very-light-grey">
  <div class="grid-2 gap fr-container">
    <div class="fr-pt-4w">
      <h5><span class="fr-icon-mail-line"></span> Abonnez-vous à notre lettre d’information</h5>
      <p>
        Retrouvez les dernières actualités du projet : partenariats, intégration de nouveaux
        modèles, publications de jeux de données et nouvelles fonctionnalités !
      </p>
    </div>
    <div class="fr-mb-4w fr-mb-md-0">
      <form
        id="newletter"
        name="mbform"
        method="POST"
        target="_blank"
        action="https://infolettres.duministeredelaculture.fr/form/65547/40/form.aspx"
        class="flex h-full items-center"
      >
        <input
          type="email"
          class="fr-input"
          id="formItem-mbtext-email"
          name="formItem-mbtext-email"
          value=""
          data-value="**MBV_EMAIL**"
          placeholder="Votre adresse électronique"
        /><input type="hidden" name="required-formItem-mbtext-email" value="true" /><input
          class="fr-btn purple-btn"
          type="submit"
          value="S’abonner"
          data-contentparameter-formsubmit="S’abonner"
          data-contentparameter-formsubmit-type="50"
          data-parameter-responsivefont-size=""
          data-parameter-responsivefont-size-type="30"
          data-parameter-responsiveline-height=""
          data-parameter-responsiveline-height-type="30"
        />
        <input type="hidden" name="status" id="status" value="submit" />
        <input type="hidden" name="accountidhidden" id="accountidhidden" value="65547" />
      </form>
    </div>
  </div>
</section>

<Snackbar />

<style>
  @media (prefers-color-scheme: light) {
    #formItem-mbtext-email.fr-input {
      background-color: white;
    }
  }

  .grid-2 {
    display: grid;
    grid-template-columns: 1fr;
  }

  @media (min-width: 62em) {
    .grid-2 {
      grid-auto-rows: 1fr;
      grid-template-columns: 1fr 1fr;
    }
  }

  .fr-icon-mail-line:after,
  .fr-icon-mail-line:before {
    background-color: var(--blue-france-main-525);
    /* 6A6AF4 */
    -webkit-mask-image: url(assets/dsfr/icons/business/mail-line.svg);
    mask-image: url(assets/dsfr/icons/business/mail-line.svg);
  }

  .fr-icon-arrow-up-line:after,
  .fr-icon-arrow-up-line:before {
    background-color: var(--text-action-high-blue-france);
    -webkit-mask-image: url('assets/dsfr/icons/system/arrow-up-line.svg');
    mask-image: url('assets/dsfr/icons/system/arrow-up-line.svg');
  }
</style>
