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

<form
  id="newletter"
  name="mbform"
  method="POST"
  target="_blank"
  action="https://infolettres.duministeredelaculture.fr/form/65547/40/form.aspx"
  class="align-center flex h-full"
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

<Snackbar />
