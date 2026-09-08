<script lang="ts">
  import { resolve } from '$app/paths'
  import LegalPresentationPreview from '$components/admin/LegalPresentationPreview.svelte'
  import { Button, Textarea } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api } from '$lib/fastapi-client'
  import type { LegalPresentation } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
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
    const presentation: LegalPresentation = {
      arena: {
        title: arenaTitle,
        introduction: arenaIntroduction,
        checkbox_label: arenaCheckboxLabel,
        button_label: arenaButtonLabel || null
      },
      sign_in: {
        checkbox_label: signInCheckboxLabel
      }
    }

    try {
      await api.request('/admin/legal/presentation', {
        method: 'PUT',
        body: JSON.stringify({ presentation })
      })
      useToast(m['admin.legal.participation.saved'](), 4000)
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      saving = false
    }
  }
</script>

<PageLayout
  seoTitle={m['admin.legal.participation.title']()}
  title={m['admin.legal.participation.title']()}
  subtitle={m['admin.legal.participation.subtitle']()}
>
  <p class="fr-mb-6v">
    <a class="fr-link fr-icon-arrow-left-line fr-link--icon-left" href={resolve('/admin/legal')}>
      {m['admin.legal.back']()}
    </a>
  </p>

  {#if loading}
    <p role="status">{m['admin.legal.participation.loading']()}</p>
  {:else}
    <form onsubmit={save} class="max-w-[1200px]" aria-labelledby="journey-form-title">
      <h2 id="journey-form-title" class="fr-h3 fr-mb-2v">
        {m['admin.legal.participation.formTitle']()}
      </h2>

      <section aria-labelledby="arena-section-title">
        <h3 id="arena-section-title" class="fr-h4">
          {m['admin.legal.participation.arenaTitle']()}
        </h3>
        <p>{m['admin.legal.participation.arenaDescription']()}</p>
        <div class="fr-grid-row fr-grid-row--gutters">
          <div class="fr-col-12 fr-col-lg-7">
            <Textarea
              id="arena-presentation-title"
              label={m['admin.legal.participation.modalTitle']()}
              rows={2}
              maxlength={200}
              required
              bind:value={arenaTitle}
            />
            <Textarea
              id="arena-presentation-introduction"
              label={m['admin.legal.participation.introduction']()}
              help={m['admin.legal.markdownHelp']()}
              groupClass="fr-mt-4v"
              rows={4}
              maxlength={2000}
              required
              bind:value={arenaIntroduction}
            />
            <Textarea
              id="arena-presentation-checkbox"
              label={m['admin.legal.participation.checkboxLabel']()}
              help={m['admin.legal.markdownHelp']()}
              groupClass="fr-mt-4v"
              rows={5}
              maxlength={2000}
              required
              bind:value={arenaCheckboxLabel}
            />
            <Textarea
              id="arena-presentation-button"
              label={m['admin.legal.participation.buttonLabel']()}
              groupClass="fr-mt-4v"
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
        <h3 id="sign-in-section-title" class="fr-h4">
          {m['admin.legal.participation.signInTitle']()}
        </h3>
        <p>{m['admin.legal.participation.signInDescription']()}</p>
        <div class="fr-grid-row fr-grid-row--gutters">
          <div class="fr-col-12 fr-col-lg-7">
            <Textarea
              id="sign-in-presentation-checkbox"
              label={m['admin.legal.participation.checkboxLabel']()}
              help={m['admin.legal.markdownHelp']()}
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
          text={saving
            ? m['admin.legal.participation.saving']()
            : m['admin.legal.participation.save']()}
          disabled={saving}
        />
      </div>
    </form>
  {/if}
</PageLayout>
