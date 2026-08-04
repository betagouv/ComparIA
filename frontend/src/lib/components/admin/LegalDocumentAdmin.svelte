<script lang="ts">
  import { resolve } from '$app/paths'
  import { Alert, Badge, Button, Input, Select, Textarea } from '$components/dsfr'
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import { PRIVACY_POLICY_PATH, TERMS_PATH } from '$lib/consent'
  import { api } from '$lib/fastapi-client'
  import type { AdminLegalDocument, PublishLegalDocumentBody } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  let { kind }: { kind: AdminLegalDocument['kind'] } = $props()

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

  const copy = $derived(
    kind === 'terms'
      ? {
          endpoint: '/admin/legal/terms',
          publicPage: resolve(TERMS_PATH),
          title: m['admin.legal.terms.title'](),
          contentLabel: m['admin.legal.terms.contentLabel'](),
          draftTitle: m['admin.legal.terms.draftTitle'](),
          emptyDescription: m['admin.legal.terms.emptyDescription']()
        }
      : {
          endpoint: '/admin/legal/privacy-policy',
          publicPage: resolve(PRIVACY_POLICY_PATH),
          title: m['admin.legal.privacy.title'](),
          contentLabel: m['admin.legal.privacy.contentLabel'](),
          draftTitle: m['admin.legal.privacy.draftTitle'](),
          emptyDescription: m['admin.legal.privacy.emptyDescription']()
        }
  )

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
      documents = await api.request<AdminLegalDocument[]>(copy.endpoint)
      try {
        activeDocument = await api.request<AdminLegalDocument>(
          `${copy.endpoint}/current?locale=${encodeURIComponent(locale)}`
        )
      } catch {
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
    if (!confirmed) return
    publishing = true
    try {
      const body: PublishLegalDocumentBody = {
        version,
        locale,
        content,
        effective_at: effectiveAt ? new Date(effectiveAt).toISOString() : null,
        confirm_publication: true
      }
      await api.request(copy.endpoint, { method: 'POST', body: JSON.stringify(body) })
      useToast(m['admin.legal.document.published'](), 4000)
      editorOpen = false
      await loadDocuments()
    } catch (err) {
      useToast((err as Error).message, 6000, 'error')
    } finally {
      publishing = false
    }
  }
</script>

<section class="max-w-[1000px]" aria-label={copy.title}>
  {#if loading}
    <p class="fr-text--sm">{m['admin.legal.document.loading']()}</p>
  {:else if !editorOpen}
    {#if activeDocument}
      {#if activeDocument.seeded}
        <Alert
          title={m['admin.legal.document.seededTitle']()}
          variant="warning"
          class="fr-mb-4v"
          role="status"
        >
          <p>{m['admin.legal.document.seededDescription']()}</p>
        </Alert>
      {/if}
      <div class="fr-card fr-card--shadow fr-p-5w fr-mb-6v">
        <div class="gap-3 md:flex-row md:items-start md:justify-between flex flex-col">
          <div>
            <Badge variant="green" size="sm" text={m['admin.legal.document.inForce']()} />
            <h2 class="fr-h3 fr-mt-2v fr-mb-1v">
              {m['admin.legal.document.version']({ version: activeDocument.version })}
            </h2>
            <p class="fr-text--sm fr-mb-0">
              {m['admin.legal.document.effectiveSince']({
                date: formatDate(activeDocument.effective_at)
              })}
            </p>
          </div>
          <div class="gap-2 flex flex-wrap">
            <a class="fr-btn fr-btn--secondary" href={copy.publicPage} target="_blank">
              {m['admin.legal.document.publicPage']()}
            </a>
            <Button text={m['admin.legal.document.prepare']()} onclick={startDraft} />
          </div>
        </div>
        <details class="fr-mt-4v">
          <summary>{m['admin.legal.document.read']()}</summary>
          <div class="fr-p-4w fr-mt-3v bg-[--background-contrast-grey]">
            <Markdown
              message={activeDocument.content}
              sanitize_html
              header_links
              variant="document"
            />
          </div>
        </details>
      </div>
    {:else}
      <Alert
        title={m['admin.legal.document.emptyTitle']()}
        variant="warning"
        class="fr-mb-4v"
        role="status"
      >
        <p>{copy.emptyDescription}</p>
      </Alert>
      <Button text={m['admin.legal.document.create']()} onclick={startDraft} />
    {/if}

    {#if scheduledDocuments.length > 0}
      <h2 class="fr-h4 fr-mt-8v">{m['admin.legal.document.scheduled']()}</h2>
      {#each scheduledDocuments as document (document.id)}
        <p>
          {m['admin.legal.document.versionOn']({
            version: document.version,
            date: formatDate(document.effective_at)
          })}
        </p>
      {/each}
    {/if}

    <h2 class="fr-h4 fr-mt-8v">{m['admin.legal.document.history']()}</h2>
    {#if historicalDocuments.length > 0}
      {#each historicalDocuments as document (document.id)}
        <details class="fr-card fr-p-3w fr-mb-2v">
          <summary>
            {m['admin.legal.document.versionOn']({
              version: document.version,
              date: formatDate(document.effective_at)
            })}
          </summary>
          <div class="fr-p-3w">
            <Markdown message={document.content} sanitize_html variant="document" />
          </div>
        </details>
      {/each}
    {:else}
      <p class="fr-text--sm">{m['admin.legal.document.historyEmpty']()}</p>
    {/if}
  {:else}
    <form onsubmit={publish} aria-labelledby="legal-document-draft-title">
      <Badge variant="yellow" size="sm" text={m['admin.legal.document.unpublished']()} />
      <div class="gap-4 md:flex-row md:items-start md:justify-between flex flex-col">
        <h2 id="legal-document-draft-title" class="fr-h3 fr-mt-2v fr-mb-1v">{copy.draftTitle}</h2>
        <Button
          variant="secondary"
          text={m['admin.legal.document.leave']()}
          onclick={() => (editorOpen = false)}
        />
      </div>

      <div class="fr-stepper fr-mb-6v max-w-[800px]">
        <h3 class="fr-stepper__title">
          {reviewing
            ? m['admin.legal.document.stepReview']()
            : m['admin.legal.document.stepWrite']()}
          <span class="fr-stepper__state">
            {m['admin.legal.document.stepState']({ current: reviewing ? 2 : 1 })}
          </span>
        </h3>
        <div
          class="fr-stepper__steps"
          data-fr-current-step={reviewing ? 2 : 1}
          data-fr-steps="2"
        ></div>
        {#if !reviewing}
          <p class="fr-stepper__details">
            <span class="fr-text--bold">{m['admin.legal.document.nextStep']()}</span>
            {m['admin.legal.document.stepReview']()}
          </p>
        {/if}
      </div>

      {#if !reviewing}
        <div class="fr-grid-row fr-grid-row--gutters">
          <div class="fr-col-12 fr-col-lg-7">
            <Textarea
              id="legal-document-content"
              label={copy.contentLabel}
              help={m['admin.legal.markdownHelp']()}
              rows={24}
              maxlength={100000}
              required
              bind:value={content}
            />
          </div>
          <aside class="fr-col-12 fr-col-lg-5" aria-label={m['admin.legal.document.preview']()}>
            <p class="fr-label fr-mb-2v">{m['admin.legal.document.preview']()}</p>
            <div class="fr-p-4w bg-[--background-contrast-grey]">
              {#if content.trim()}
                <Markdown message={content} sanitize_html header_links variant="document" />
              {:else}
                <p class="fr-text--sm">{m['admin.legal.document.previewEmpty']()}</p>
              {/if}
            </div>
          </aside>
        </div>
      {:else}
        <div class="fr-grid-row fr-grid-row--gutters">
          <div class="fr-col-12 fr-col-md-6">
            <Input
              id="legal-document-version"
              label={m['admin.legal.document.versionLabel']()}
              help={m['admin.legal.document.versionHelp']()}
              maxlength={64}
              required
              bind:value={version}
            />
          </div>
          <div class="fr-col-12 fr-col-md-6">
            <Select
              id="legal-document-locale"
              label={m['admin.legal.document.locale']()}
              reserveHintSpace
              options={localeOptions}
              bind:selected={locale}
            />
          </div>
        </div>
        <Input
          id="legal-document-effective-at"
          type="datetime-local"
          label={m['admin.legal.document.effectiveAt']()}
          help={m['admin.legal.document.effectiveAtHelp']()}
          groupClass="fr-mt-4v"
          bind:value={effectiveAt}
        />
        <div class="fr-checkbox-group fr-mt-6v">
          <input id="legal-document-confirmation" type="checkbox" bind:checked={confirmed} />
          <label class="fr-label" for="legal-document-confirmation">
            {m['admin.legal.document.confirm']()}
          </label>
        </div>
      {/if}

      <div class="gap-3 fr-mt-6v flex flex-wrap justify-between">
        <div>
          {#if reviewing}
            <Button
              variant="secondary"
              text={m['admin.legal.document.backToWriting']()}
              onclick={() => (reviewing = false)}
            />
          {/if}
        </div>
        {#if reviewing}
          <Button
            type="submit"
            text={publishing
              ? m['admin.legal.document.publishing']()
              : m['admin.legal.document.publish']()}
            disabled={publishing || !confirmed}
          />
        {:else}
          <Button
            text={m['admin.legal.document.continue']()}
            icon="arrow-right-line"
            iconPos="right"
            onclick={() => (reviewing = true)}
          />
        {/if}
      </div>
    </form>
  {/if}
</section>
