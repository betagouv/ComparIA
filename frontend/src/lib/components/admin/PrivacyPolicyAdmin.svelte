<script lang="ts">
  import { resolve } from '$app/paths'
  import MarkdownEditor from '$components/admin/MarkdownEditor.svelte'
  import { Alert, Badge, Button, Input, Select } from '$components/dsfr'
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import { api } from '$lib/fastapi-client'
  import type { AdminLegalDocument, PublishPrivacyPolicyBody } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { onMount } from 'svelte'

  type EditorStep = 'content' | 'review'

  let { standalone = false }: { standalone?: boolean } = $props()

  const localeOptions = [{ value: 'fr', label: 'Français' }]
  let loading = $state(true)
  let publishing = $state(false)
  let editorOpen = $state(false)
  let currentStep = $state<EditorStep>('content')
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
      documents = await api.request<AdminLegalDocument[]>('/admin/legal/privacy-policy')
      if (documents.length > 0) {
        try {
          activeDocument = await api.request<AdminLegalDocument>(
            `/admin/legal/privacy-policy/current?locale=${encodeURIComponent(locale)}`
          )
        } catch {
          activeDocument = null
        }
      } else {
        activeDocument = null
      }
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      loading = false
    }
  }

  function startDraft() {
    content = activeDocument?.content ?? ''
    version = ''
    effectiveAt = ''
    confirmed = false
    currentStep = 'content'
    editorOpen = true
  }

  function closeDraft() {
    editorOpen = false
    confirmed = false
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
    if (!confirmed) return
    publishing = true
    try {
      const body: PublishPrivacyPolicyBody = {
        version,
        locale,
        content,
        effective_at: effectiveAt ? new Date(effectiveAt).toISOString() : null,
        confirm_publication: true
      }
      await api.request('/admin/legal/privacy-policy', {
        method: 'POST',
        body: JSON.stringify(body)
      })
      useToast('La politique de confidentialité a été publiée.', 4000)
      editorOpen = false
      await loadDocuments()
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      publishing = false
    }
  }
</script>

<section
  class={standalone ? 'max-w-[1000px]' : 'fr-mt-12v max-w-[1000px]'}
  aria-label={standalone ? 'Politique de confidentialité' : undefined}
  aria-labelledby={standalone ? undefined : 'privacy-policy-title'}
>
  {#if standalone}
    <h2 class="fr-sr-only">Gestion de la politique de confidentialité</h2>
  {/if}
  {#if !standalone}
    <div class="fr-mb-6v border-t pt-8">
      <h2 id="privacy-policy-title" class="fr-h2 fr-mb-2v">Politique de confidentialité</h2>
      <p>
        Gérez le document qui explique les traitements de données personnelles. Sa publication est
        indépendante des conditions acceptées par les utilisateurs.
      </p>
    </div>
  {/if}

  {#if loading}
    <p class="fr-text--sm">Chargement de la politique…</p>
  {:else if !editorOpen}
    {#if activeDocument}
      <div class="fr-card fr-card--shadow fr-p-5w fr-mb-6v">
        <div class="gap-3 md:flex-row md:items-start md:justify-between flex flex-col">
          <div>
            <Badge variant="green" size="sm" text="En vigueur" />
            <h3 class="fr-h4 fr-mt-2v fr-mb-1v">Version {activeDocument.version}</h3>
            <p class="fr-text--sm fr-mb-0">
              Publiée depuis le {formatDate(activeDocument.effective_at)}.
            </p>
          </div>
          <div class="gap-2 flex flex-wrap">
            <a
              class="fr-btn fr-btn--secondary"
              href={resolve('/arene/donnees-personnelles')}
              target="_blank"
            >Voir dans l’arène</a>
            <Button text="Préparer une nouvelle politique" onclick={startDraft} />
          </div>
        </div>
        <details class="fr-mt-4v">
          <summary>Consulter la politique active</summary>
          <div class="fr-p-4w fr-mt-3v bg-[--background-contrast-grey]">
            <Markdown message={activeDocument.content} sanitize_html header_links />
          </div>
        </details>
      </div>
    {:else}
      <Alert title="Aucune politique publiée" variant="warning" class="fr-mb-4v">
        <p>
          La page publique affiche encore le contenu intégré à l’application. Publiez une première
          version pour la gérer depuis ce back-office.
        </p>
      </Alert>
      <Button text="Créer la politique de confidentialité" onclick={startDraft} />
    {/if}

    {#if scheduledDocuments.length > 0}
      <h3 class="fr-h4 fr-mt-8v">Publications programmées</h3>
      {#each scheduledDocuments as document (document.id)}
        <p><strong>Version {document.version}</strong> — {formatDate(document.effective_at)}</p>
      {/each}
    {/if}

    {#if historicalDocuments.length > 0}
      <h3 class="fr-h4 fr-mt-8v">Historique de la politique</h3>
      {#each historicalDocuments as document (document.id)}
        <details class="fr-card fr-p-3w fr-mb-2v">
          <summary>Version {document.version} — {formatDate(document.effective_at)}</summary>
          <div class="fr-p-3w"><Markdown message={document.content} sanitize_html /></div>
        </details>
      {/each}
    {/if}
  {:else}
    <form onsubmit={publish} aria-labelledby="privacy-draft-title">
      <Badge variant="yellow" size="sm" text="Non publiée" />
      <div class="gap-4 md:flex-row md:items-start md:justify-between flex flex-col">
        <div>
          <h3 id="privacy-draft-title" class="fr-h3 fr-mt-2v fr-mb-1v">
            Nouvelle politique de confidentialité
          </h3>
          <p class="fr-text--sm">La page publique ne changera qu’après publication.</p>
        </div>
        <Button variant="secondary" text="Quitter sans publier" onclick={closeDraft} />
      </div>

      <div class="fr-stepper fr-mb-6v max-w-[800px]">
        <h4 class="fr-stepper__title">
          {currentStep === 'content' ? 'Rédiger la politique' : 'Vérifier et publier'}
          <span class="fr-stepper__state">Étape {currentStep === 'content' ? 1 : 2} sur 2</span>
        </h4>
        <div
          class="fr-stepper__steps"
          data-fr-current-step={currentStep === 'content' ? 1 : 2}
          data-fr-steps="2"
        ></div>
        {#if currentStep === 'content'}
          <p class="fr-stepper__details">
            <span class="fr-text--bold">Étape suivante :</span> Vérifier et publier
          </p>
        {/if}
      </div>

      {#if currentStep === 'content'}
        <div class="fr-grid-row fr-grid-row--gutters">
          <div class="fr-col-12 fr-col-lg-7">
            <MarkdownEditor
              id="privacy-policy-content"
              label="Contenu de la politique de confidentialité"
              help="Utilisez la barre d’outils ou saisissez directement du Markdown."
              rows={24}
              maxlength={100000}
              required
              bind:value={content}
            />
          </div>
          <aside class="fr-col-12 fr-col-lg-5" aria-label="Aperçu de la politique">
            <p class="fr-text--sm fr-text--bold">Aperçu</p>
            <div class="fr-p-4w bg-[--background-contrast-grey]">
              {#if content.trim()}
                <Markdown message={content} sanitize_html header_links />
              {:else}
                <p class="fr-text--sm">L’aperçu apparaîtra ici.</p>
              {/if}
            </div>
          </aside>
        </div>
      {:else}
        <Alert title="Publication définitive" variant="warning" class="fr-mb-6v">
          <p>Une politique publiée est conservée dans l’historique et ne peut plus être modifiée.</p>
        </Alert>
        <div class="fr-grid-row fr-grid-row--gutters">
          <div class="fr-col-12 fr-col-md-6">
            <Input
              id="privacy-policy-version"
              label="Référence de la nouvelle version"
              help="Par exemple 2026.1. Cette référence doit être unique."
              maxlength={64}
              required
              bind:value={version}
            />
          </div>
          <div class="fr-col-12 fr-col-md-6">
            <Select
              id="privacy-policy-locale"
              label="Langue"
              options={localeOptions}
              bind:selected={locale}
            />
          </div>
        </div>
        <Input
          id="privacy-policy-effective-at"
          type="datetime-local"
          label="Date d’entrée en vigueur"
          help="Laissez vide pour publier immédiatement."
          bind:value={effectiveAt}
        />
        <div class="fr-checkbox-group fr-mt-6v">
          <input id="privacy-policy-confirmation" type="checkbox" bind:checked={confirmed} />
          <label class="fr-label" for="privacy-policy-confirmation">
            J’ai relu la politique et je comprends que cette version ne pourra plus être modifiée.
          </label>
        </div>
      {/if}

      <div class="gap-3 fr-mt-6v pt-4 flex flex-wrap justify-between border-t">
        <div>
          {#if currentStep === 'review'}
            <Button
              variant="secondary"
              text="Revenir à la rédaction"
              onclick={() => (currentStep = 'content')}
            />
          {/if}
        </div>
        {#if currentStep === 'content'}
          <Button
            text="Continuer vers « Vérifier et publier »"
            icon="arrow-right-line"
            iconPos="right"
            onclick={() => (currentStep = 'review')}
          />
        {:else}
          <Button
            type="submit"
            text={publishing ? 'Publication…' : 'Publier cette politique'}
            disabled={publishing || !confirmed}
          />
        {/if}
      </div>
    </form>
  {/if}
</section>
