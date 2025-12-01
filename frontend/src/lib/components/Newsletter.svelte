<script lang="ts">
  import { Button, Icon, Link } from '$components/dsfr'
  import { useToast } from '$lib/helpers/useToast.svelte'

  async function handleNewsletterSubmit(e: SubmitEvent) {
    e.preventDefault() // Prevent the default form submission
    const form = e.target as HTMLFormElement
    const formData = new FormData(form)

    try {
      const response = await fetch(form.action, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        // @ts-ignore (legit)
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
        useToast('Merci, votre inscription à la newsletter a été prise en compte.', 2000)
      } else {
        useToast("Erreur lors de l'inscription à la newsletter.", 2000, 'error')
      }
    } catch (error) {
      console.error('Newsletter subscription error:', error)
      useToast("Echec de l'inscription.", 2000, 'error')
    }
  }
</script>

<div class="mt-3 text-center">
  <div class="bg-light-info inline-block p-3">
    <Link href="#" text="Haut de page" icon="arrow-up-line" class="pb-1!" />
  </div>
</div>
<section class="fr-container--fluid bg-light-info">
  <div class="fr-container pt-8 pb-10 lg:grid lg:grid-cols-2 lg:gap-6">
    <div>
      <h5 class="mb-2! flex items-center">
        <Icon icon="mail-line" size="lg" block class="text-primary me-2" />
        Abonnez-vous à notre lettre d’information
      </h5>
      <p class="text-sm! lg:mb-0!">
        Retrouvez les dernières actualités du projet : partenariats, intégration de nouveaux
        modèles, publications de jeux de données et nouvelles fonctionnalités !
      </p>
    </div>
    <div class="">
      <form
        id="newletter"
        name="mbform"
        method="POST"
        target="_blank"
        action="https://infolettres.duministeredelaculture.fr/form/65547/40/form.aspx"
        class="flex h-full items-center"
        onsubmit={handleNewsletterSubmit}
      >
        <input
          type="email"
          id="formItem-mbtext-email"
          name="formItem-mbtext-email"
          value=""
          data-value="**MBV_EMAIL**"
          placeholder="Votre adresse électronique"
          class="fr-input rounded-tl-sm bg-white!"
        />
        <input type="hidden" name="required-formItem-mbtext-email" value="true" />
        <Button
          type="submit"
          text="S’abonner"
          data-contentparameter-formsubmit="S’abonner"
          data-contentparameter-formsubmit-type="50"
          data-parameter-responsivefont-size=""
          data-parameter-responsivefont-size-type="30"
          data-parameter-responsiveline-height=""
          data-parameter-responsiveline-height-type="30"
          cornered
          class="rounded-tr-sm"
        />
        <input type="hidden" name="status" id="status" value="submit" />
        <input type="hidden" name="accountidhidden" id="accountidhidden" value="65547" />
      </form>
    </div>
  </div>
</section>
