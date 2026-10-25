<script lang="ts">
  import { goto } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Alert, Badge, Button } from '$components/dsfr'
  import { MarkdownCode as Markdown } from '$components/markdown'
  import { PRIVACY_POLICY_PATH, TERMS_PATH } from '$lib/consent'
  import type { AdminLegalDocument } from '$lib/generated/admin'
  import type { LegalDocumentKeys } from '$lib/generated/constants'
  import { m } from '$lib/i18n/messages'
  import type { PageProps } from './$types'

  const { data, params }: PageProps = $props()

  const kind = $derived(params.legalDoc as LegalDocumentKeys)
  let documents = $derived<AdminLegalDocument[]>(data.documents.history)
  let activeDocument = $derived<AdminLegalDocument | null>(data.documents.current)

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

  function formatDate(value: string) {
    return new Intl.DateTimeFormat('fr-FR', {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone: 'Europe/Paris'
    }).format(new Date(value))
  }
</script>

<section>
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
          <a
            class="fr-btn fr-btn--secondary"
            href={kind === 'terms' ? TERMS_PATH : PRIVACY_POLICY_PATH}
            target="_blank"
          >
            {m['admin.legal.document.publicPage']()}
          </a>
          <Button
            text={m['admin.legal.document.prepare']()}
            onclick={() => goto(resolve(`/admin/legal/${kind}/create`))}
          />
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
      <p>{m[`admin.legal.${kind}.emptyDescription`]()}</p>
    </Alert>
    <Button
      text={m['admin.legal.document.create']()}
      onclick={() => goto(resolve(`/admin/legal/${kind}/create`))}
    />
  {/if}
</section>
<section>
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
</section>

<section>
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
</section>
