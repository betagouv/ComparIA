<script lang="ts">
  import { resolve } from '$app/paths'
  import MarkdownEditor from '$components/admin/MarkdownEditor.svelte'
  import { Alert, Badge, Button, Input, Select } from '$components/dsfr'
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import { CANONICAL_LEGAL_LINKS } from '$lib/consent'
  import { api } from '$lib/fastapi-client'
  import type { AdminLegalDocument, PublishTermsBody } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { onMount } from 'svelte'

  const localeOptions = [{ value: 'fr', label: 'Français' }]
  let loading = $state(true)
  let publishing = $state(false)
  let editorOpen = $state(false)
  let reviewing = $state(false)
  let documents = $state<AdminLegalDocument[]>([])
  let activeDocument = $state<AdminLegalDocument | null>(null)
  let version = $state('')
  let locale = $state('fr')
  let content = $state('')
  let effectiveAt = $state('')
  let confirmed = $state(false)

  const scheduledDocuments = $derived(
    documents.filter(
      (document) =>
        document.id !== activeDocument?.id && new Date(document.effective_at) > new Date()
    )
  )
  const historicalDocuments = $derived(
    documents.filter(
      (document) =>
        document.id !== activeDocument?.id &&
        !scheduledDocuments.some(({ id }) => id === document.id)
    )
  )

  onMount(loadDocuments)

  async function loadDocuments() {
    loading = true
    try {
      documents = await api.request<AdminLegalDocument[]>('/admin/legal/terms')
      activeDocument = await api.request<AdminLegalDocument>(
        `/admin/legal/terms/current?locale=${encodeURIComponent(locale)}`
      )
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      loading = false
    }
  }

  function startDraft() {
    if (!activeDocument) return
    content = activeDocument.content
    version = ''
    effectiveAt = ''
    confirmed = false
    reviewing = false
    editorOpen = true
  }

  function formatDate(value: string) {
    return new Intl.DateTimeFormat('fr-FR', {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone: 'Europe/Paris'
    }).format(new Date(value))
  }

  async function publish(e: SubmitEvent) {
    e.preventDefault()
    if (!confirmed || !activeDocument?.presentation) return
    publishing = true
    try {
      const presentation = activeDocument.presentation
      const body: PublishTermsBody = {
        version,
        locale,
        content,
        presentation: {
          arena: {
            ...presentation.arena,
            links: CANONICAL_LEGAL_LINKS as PublishTermsBody['presentation']['arena']['links']
          },
          sign_in: {
            ...presentation.sign_in,
            links: CANONICAL_LEGAL_LINKS as PublishTermsBody['presentation']['sign_in']['links']
          }
        },
        effective_at: effectiveAt ? new Date(effectiveAt).toISOString() : null,
        confirm_publication: true
      }
      await api.request('/admin/legal/terms', {
        method: 'POST',
        body: JSON.stringify(body)
      })
      useToast('La nouvelle version des conditions a été publiée.', 4000)
      editorOpen = false
      await loadDocuments()
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      publishing = false
    }
  }
</script>

<section class="max-w-[1000px]" aria-label="Conditions d’utilisation">
  {#if loading}
    <p class="fr-text--sm">Chargement des conditions…</p>
  {:else if !editorOpen}
    {#if activeDocument}
      <div class="fr-card fr-card--shadow fr-p-5w fr-mb-6v">
        <div class="gap-3 md:flex-row md:items-start md:justify-between flex flex-col">
          <div>
            <Badge variant="green" size="sm" text="En vigueur" />
            <h2 class="fr-h3 fr-mt-2v fr-mb-1v">Version {activeDocument.version}</h2>
            <p class="fr-text--sm fr-mb-0">
              Applicable depuis le {formatDate(activeDocument.effective_at)}.
            </p>
          </div>
          <div class="gap-2 flex flex-wrap">
            <a
              class="fr-btn fr-btn--secondary"
              href={resolve('/arene/modalites')}
              target="_blank"
            >Voir dans l’arène</a>
            <Button text="Préparer une nouvelle version" onclick={startDraft} />
          </div>
        </div>
        <details class="fr-mt-4v">
          <summary>Consulter les conditions actives</summary>
          <div class="fr-p-4w fr-mt-3v bg-[--background-contrast-grey]">
            <Markdown message={activeDocument.content} sanitize_html header_links />
          </div>
        </details>
      </div>
    {/if}

    {#if scheduledDocuments.length > 0}
      <h2 class="fr-h4 fr-mt-8v">Publications programmées</h2>
      {#each scheduledDocuments as document (document.id)}
        <p><strong>Version {document.version}</strong> — {formatDate(document.effective_at)}</p>
      {/each}
    {/if}

    <h2 class="fr-h4 fr-mt-8v">Historique</h2>
    {#if historicalDocuments.length > 0}
      {#each historicalDocuments as document (document.id)}
        <details class="fr-card fr-p-3w fr-mb-2v">
          <summary>Version {document.version} — {formatDate(document.effective_at)}</summary>
          <div class="fr-p-3w"><Markdown message={document.content} sanitize_html /></div>
        </details>
      {/each}
    {:else}
      <p class="fr-text--sm">Aucune ancienne version.</p>
    {/if}
  {:else}
    <form onsubmit={publish} aria-labelledby="terms-document-draft-title">
      <Badge variant="yellow" size="sm" text="Non publiée" />
      <div class="gap-4 md:flex-row md:items-start md:justify-between flex flex-col">
        <div>
          <h2 id="terms-document-draft-title" class="fr-h3 fr-mt-2v fr-mb-1v">
            Nouvelles conditions d’utilisation
          </h2>
          <p class="fr-text--sm">
            Le parcours de participation actuel sera conservé avec cette nouvelle version.
          </p>
        </div>
        <Button
          variant="secondary"
          text="Quitter sans publier"
          onclick={() => (editorOpen = false)}
        />
      </div>

      <div class="fr-stepper fr-mb-6v max-w-[800px]">
        <h3 class="fr-stepper__title">
          {reviewing ? 'Vérifier et publier' : 'Rédiger les conditions'}
          <span class="fr-stepper__state">Étape {reviewing ? 2 : 1} sur 2</span>
        </h3>
        <div
          class="fr-stepper__steps"
          data-fr-current-step={reviewing ? 2 : 1}
          data-fr-steps="2"
        ></div>
        {#if !reviewing}
          <p class="fr-stepper__details">
            <span class="fr-text--bold">Étape suivante :</span> Vérifier et publier
          </p>
        {/if}
      </div>

      {#if !reviewing}
        <div class="fr-grid-row fr-grid-row--gutters">
          <div class="fr-col-12 fr-col-lg-7">
            <MarkdownEditor
              id="terms-document-content"
              label="Contenu des conditions d’utilisation"
              help="Utilisez la barre d’outils ou saisissez directement du Markdown."
              rows={24}
              maxlength={100000}
              required
              bind:value={content}
            />
          </div>
          <aside class="fr-col-12 fr-col-lg-5" aria-label="Aperçu des conditions">
            <p class="fr-text--sm fr-text--bold">Aperçu</p>
            <div class="fr-p-4w bg-[--background-contrast-grey]">
              <Markdown message={content} sanitize_html header_links />
            </div>
          </aside>
        </div>
      {:else}
        <Alert title="Publication définitive" variant="warning" class="fr-mb-6v">
          <p>Une version publiée est conservée dans l’historique et ne peut plus être modifiée.</p>
        </Alert>
        <div class="fr-grid-row fr-grid-row--gutters">
          <div class="fr-col-12 fr-col-md-6">
            <Input
              id="terms-document-version"
              label="Référence de la nouvelle version"
              help="Par exemple 2026.2. Cette référence doit être unique."
              maxlength={64}
              required
              bind:value={version}
            />
          </div>
          <div class="fr-col-12 fr-col-md-6">
            <Select
              id="terms-document-locale"
              label="Langue"
              options={localeOptions}
              bind:selected={locale}
            />
          </div>
        </div>
        <Input
          id="terms-document-effective-at"
          type="datetime-local"
          label="Date d’entrée en vigueur"
          help="Laissez vide pour publier immédiatement."
          bind:value={effectiveAt}
        />
        <div class="fr-checkbox-group fr-mt-6v">
          <input id="terms-document-confirmation" type="checkbox" bind:checked={confirmed} />
          <label class="fr-label" for="terms-document-confirmation">
            J’ai relu les conditions et je comprends que cette version ne pourra plus être modifiée.
          </label>
        </div>
      {/if}

      <div class="gap-3 fr-mt-6v pt-4 flex flex-wrap justify-between border-t">
        <div>
          {#if reviewing}
            <Button
              variant="secondary"
              text="Revenir à la rédaction"
              onclick={() => (reviewing = false)}
            />
          {/if}
        </div>
        {#if reviewing}
          <Button
            type="submit"
            text={publishing ? 'Publication…' : 'Publier ces conditions'}
            disabled={publishing || !confirmed}
          />
        {:else}
          <Button
            text="Continuer vers « Vérifier et publier »"
            icon="arrow-right-line"
            iconPos="right"
            onclick={() => (reviewing = true)}
          />
        {/if}
      </div>
    </form>
  {/if}
</section>
