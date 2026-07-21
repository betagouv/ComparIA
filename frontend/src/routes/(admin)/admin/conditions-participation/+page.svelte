<script lang="ts">
  import { resolve } from '$app/paths'
  import LegalPresentationPreview from '$components/admin/LegalPresentationPreview.svelte'
  import MarkdownEditor from '$components/admin/MarkdownEditor.svelte'
  import { Alert, Button } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import { CANONICAL_LEGAL_LINKS } from '$lib/consent'
  import type { LegalPresentation } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { onMount } from 'svelte'

  let loading = $state(true)
  let saving = $state(false)
  let arenaTitle = $state('')
  let arenaIntroduction = $state('')
  let arenaCheckboxLabel = $state('')
  let arenaButtonLabel = $state('')
  let signInCheckboxLabel = $state('')

  onMount(loadPresentation)

  async function loadPresentation() {
    loading = true
    try {
      const presentation = await api.request<LegalPresentation>('/admin/legal/presentation')
      arenaTitle = presentation.arena.title
      arenaIntroduction = presentation.arena.introduction
      arenaCheckboxLabel = presentation.arena.checkbox_label
      arenaButtonLabel = presentation.arena.button_label ?? ''
      signInCheckboxLabel = presentation.sign_in.checkbox_label
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      loading = false
    }
  }

  async function save(e: SubmitEvent) {
    e.preventDefault()
    saving = true
    const links = CANONICAL_LEGAL_LINKS as LegalPresentation['arena']['links']
    const presentation: LegalPresentation = {
      arena: {
        title: arenaTitle,
        introduction: arenaIntroduction,
        checkbox_label: arenaCheckboxLabel,
        links,
        button_label: arenaButtonLabel || null
      },
      sign_in: {
        checkbox_label: signInCheckboxLabel,
        links
      }
    }

    try {
      await api.request('/admin/legal/presentation', {
        method: 'PUT',
        body: JSON.stringify({ presentation })
      })
      useToast('Le parcours de participation a été enregistré.', 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      saving = false
    }
  }
</script>

<PageLayout
  seoTitle="Parcours de participation"
  title="Parcours de participation"
  subtitle="Configurez les informations présentées avant le premier message et à la connexion."
>
  <p class="fr-mb-6v">
    <a class="fr-link fr-icon-arrow-left-line fr-link--icon-left" href={resolve('/admin/legal')}
      >Retour aux documents juridiques</a
    >
  </p>

  {#if loading}
    <p role="status">Chargement du parcours…</p>
  {:else}
    <form onsubmit={save} class="max-w-[1200px]" aria-labelledby="journey-form-title">
      <h2 id="journey-form-title" class="fr-h3 fr-mb-2v">Modifier le parcours</h2>
      <Alert title="Une configuration simple, sans version" class="fr-mb-6v">
        <p>
          Les changements sont appliqués dès l’enregistrement. Les liens vers les conditions
          d’utilisation et la politique de confidentialité sont ajoutés automatiquement.
        </p>
      </Alert>

      <section aria-labelledby="arena-section-title">
        <h3 id="arena-section-title" class="fr-h4">Avant le premier message</h3>
        <p>
          Ce contenu apparaît lorsqu’une personne non connectée tente d’envoyer son premier message.
        </p>
        <div class="fr-grid-row fr-grid-row--gutters">
          <div class="fr-col-12 fr-col-lg-7">
            <MarkdownEditor
              id="arena-presentation-title"
              label="Titre de la fenêtre"
              mode="inline"
              rows={2}
              maxlength={200}
              required
              bind:value={arenaTitle}
            />
            <MarkdownEditor
              id="arena-presentation-introduction"
              label="Texte introductif"
              rows={4}
              maxlength={2000}
              required
              bind:value={arenaIntroduction}
            />
            <MarkdownEditor
              id="arena-presentation-checkbox"
              label="Texte associé à la case obligatoire"
              mode="inline"
              rows={5}
              maxlength={2000}
              required
              bind:value={arenaCheckboxLabel}
            />
            <MarkdownEditor
              id="arena-presentation-button"
              label="Texte du bouton de confirmation"
              mode="inline"
              allowLinks={false}
              rows={2}
              maxlength={200}
              bind:value={arenaButtonLabel}
            />
          </div>
          <div class="fr-col-12 fr-col-lg-5">
            <LegalPresentationPreview
              kind="arena"
              title={arenaTitle}
              introduction={arenaIntroduction}
              checkboxLabel={arenaCheckboxLabel}
              buttonLabel={arenaButtonLabel}
            />
          </div>
        </div>
      </section>

      <section class="fr-mt-8v" aria-labelledby="sign-in-section-title">
        <h3 id="sign-in-section-title" class="fr-h4">À la connexion</h3>
        <p>
          Cette case apparaît avant l’envoi du code de connexion et reste cochée pendant la saisie
          du code.
        </p>
        <div class="fr-grid-row fr-grid-row--gutters">
          <div class="fr-col-12 fr-col-lg-7">
            <MarkdownEditor
              id="sign-in-presentation-checkbox"
              label="Texte associé à la case obligatoire"
              mode="inline"
              rows={5}
              maxlength={2000}
              required
              bind:value={signInCheckboxLabel}
            />
          </div>
          <div class="fr-col-12 fr-col-lg-5">
            <LegalPresentationPreview kind="sign-in" checkboxLabel={signInCheckboxLabel} />
          </div>
        </div>
      </section>

      <div class="fr-mt-6v flex justify-end">
        <Button
          type="submit"
          text={saving ? 'Enregistrement…' : 'Enregistrer le parcours'}
          disabled={saving}
        />
      </div>
    </form>
  {/if}
</PageLayout>
