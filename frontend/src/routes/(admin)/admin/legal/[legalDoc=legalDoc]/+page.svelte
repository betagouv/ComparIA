<script lang="ts">
  import { goto } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { AccordionGroup, Alert, Badge, Button } from '$components/dsfr'
  import { getAuthContext } from '$lib/authContext.svelte'
  import { PRIVACY_POLICY_PATH, TERMS_PATH } from '$lib/consent'
  import type { AdminLegalDocument } from '$lib/generated/admin'
  import type { LegalDocumentKeys } from '$lib/generated/constants'
  import type { LocaleOption } from '$lib/global.svelte'
  import { getLocales } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { fromEntries } from '$lib/utils/commons'
  import type { PageProps } from './$types'

  const { data, params }: PageProps = $props()

  const kind = $derived(params.legalDoc as LegalDocumentKeys)
  let documents = $derived<AdminLegalDocument[]>(data.documents.history)
  let activeDocument = $derived(data.documents.current)
  const activeDocumentLocales = $derived(
    Object.keys(activeDocument?.content ?? {}) as LocaleOption['code'][]
  )

  const scheduledDocuments = $derived(
    documents.filter(
      (document) =>
        activeDocument?.id !== document.id && new Date(document.effective_at) > new Date()
    )
  )
  const historicalDocuments = $derived(
    documents.filter(
      (document) =>
        activeDocument?.id !== document.id &&
        !scheduledDocuments.some(({ id }) => id === document.id)
    )
  )

  const auth = getAuthContext()
  const locales = $derived(
    fromEntries(getLocales(auth.config.enabled_locales).map((l) => [l.code, l]))
  )

  function formatDate(value: string) {
    return new Intl.DateTimeFormat(getLocale(), {
      dateStyle: 'medium',
      timeStyle: 'short',
      // FIXME use server tz with long time style?
      timeZone: 'Europe/Paris'
    }).format(new Date(value))
  }
</script>

{#snippet documentList(documents: AdminLegalDocument[])}
  <div class="gap-4 flex flex-col">
    {#each documents as doc (doc.id)}
      {@const availableLocales = Object.keys(doc.content) as LocaleOption['code'][]}
      <div class="cg-border p-4">
        <h3 class="text-base! mb-3!">
          {m['admin.legal.document.versionOn']({
            version: doc.version,
            date: formatDate(doc.effective_at)
          })}
        </h3>
        <AccordionGroup
          id="accordion-{doc.version}"
          items={availableLocales.map((l) => ({
            id: l,
            label: locales[l].long,
            content: doc.content[l],
            class: 'bg-[--green-tilleul-verveine-975-75]'
          }))}
          markdown
        />
      </div>
    {/each}
  </div>
{/snippet}

<section>
  <h2 class="fr-h4">{m['admin.legal.document.read']()}</h2>

  {#if activeDocument}
    <div class="gap-4 flex flex-col">
      <div class="cg-border p-6 shadow-md">
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

        <AccordionGroup
          id="accordion-{activeDocument.version}"
          items={activeDocumentLocales.map((l) => ({
            id: l,
            label: locales[l].long,
            content: activeDocument.content[l],
            class: 'bg-[--green-tilleul-verveine-975-75]'
          }))}
          markdown
          class="mt-4"
        />
      </div>
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

{#if scheduledDocuments.length > 0}
  <section>
    <h2 class="fr-h4 fr-mt-8v">{m['admin.legal.document.scheduled']()}</h2>
    {@render documentList(scheduledDocuments)}
  </section>
{/if}

<section>
  <h2 class="fr-h4 fr-mt-8v">{m['admin.legal.document.history']()}</h2>

  {#if historicalDocuments.length > 0}
    {@render documentList(historicalDocuments)}
  {:else}
    <p class="fr-text--sm">{m['admin.legal.document.historyEmpty']()}</p>
  {/if}
</section>
