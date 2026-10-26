<script lang="ts">
  import { goto, invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Button, Textarea } from '$components/dsfr'
  import { FormInput } from '$components/form'
  import Form from '$components/form/Form.svelte'
  import FormCheckbox from '$components/form/FormCheckbox.svelte'
  import FormTranslate from '$components/form/FormTranslate.svelte'
  import UserPreview from '$components/UserPreview.svelte'
  import { getAuthContext } from '$lib/authContext.svelte'
  import type { PublishLegalDocumentBody } from '$lib/generated/admin'
  import type { LegalDocumentKeys } from '$lib/generated/constants'
  import { m } from '$lib/i18n/messages'
  import { useForm } from '$lib/stores/form.svelte'
  import type { PageProps } from './$types'

  const { data, params }: PageProps = $props()

  const kind = $derived(params.legalDoc as LegalDocumentKeys)

  const auth = getAuthContext()
  const defaultLocale = $derived(auth.config.default_locale)
  let selectedLocale = $derived(defaultLocale)
  let step = $state<'write' | 'review'>('write')

  const form = $derived(
    useForm({
      url: `/admin/legal/documents/${kind}`,
      method: 'post',
      initialData: () =>
        ({
          version: '',
          content: data.documents.current?.content ?? {},
          effective_at: null,
          confirm_publication: false as true
        }) as PublishLegalDocumentBody,
      onBeforeSubmit: (form, errors) => {
        if (!form.content[defaultLocale]) {
          // FIXME show error in FormTranslate Segmented
          errors[`content_by_locale-${defaultLocale}`] = m['form.missing_default_locale']()
          return null
        }
        return {
          ...form,
          effective_at: form.effective_at ? new Date(form.effective_at).toISOString() : null
        }
      },
      onSuccess: async () => {
        await invalidate('admin:legal')
        goto(resolve(`/admin/legal/${kind}`))
      }
    })
  )

  const currentContent = $derived(form.form.content[selectedLocale]?.trim())
</script>

<!-- FIXME using default validation for now, datetime-local without time doesn't update form -->
<Form
  id="legal-doc"
  label={m[`admin.legal.${kind}.draftTitle`]()}
  {...form}
  stickyFooter
  novalidate={false}
>
  {#if step === 'write'}
    <UserPreview id="legal-doc-preview" content={currentContent}>
      <FormTranslate
        id="content_by_locale"
        bind:value={form.form.content}
        bind:locale={selectedLocale}
      >
        {#snippet subSnippet(locale)}
          <Textarea
            id="content-{locale}"
            label={m[`admin.legal.${kind}.contentLabel`]()}
            help={m['admin.legal.markdownHelp']()}
            rows={24}
            maxlength={100000}
            required
            error={form.errors[`content_by_locale-${locale}`]}
            bind:value={form.form.content[locale]}
          />
        {/snippet}
      </FormTranslate>
    </UserPreview>
  {:else}
    <FormInput
      id="version"
      type="text"
      label={m['admin.legal.document.versionLabel']()}
      help={m['admin.legal.document.versionHelp']()}
      maxlength={64}
      required
      bind:value={form.form.version}
    />

    <FormInput
      id="effective_at"
      type="datetime-local"
      label={m['admin.legal.document.effectiveAt']()}
      help={m['admin.legal.document.effectiveAtHelp']()}
      bind:value={form.form.effective_at}
    />

    <FormCheckbox
      id="confirm_publication"
      label={m['admin.legal.document.confirm']()}
      bind:value={form.form.confirm_publication}
    />
  {/if}

  {#snippet btnSnippet()}
    {#if step === 'review'}
      <Button
        variant="secondary"
        text={m['admin.legal.document.backToWriting']()}
        onclick={() => (step = 'write')}
      />
      <Button
        type="submit"
        text={form.isBusy
          ? m['admin.legal.document.publishing']()
          : m['admin.legal.document.publish']()}
        disabled={form.isBusy || !form.form.confirm_publication}
      />
    {:else}
      <Button
        variant="secondary"
        text={m['admin.legal.document.leave']()}
        onclick={() => goto(resolve(`/admin/legal/${kind}`))}
      />
      <Button
        text={m['words.continue']()}
        icon="arrow-right-line"
        iconPos="right"
        onclick={() => (step = 'review')}
      />
    {/if}
  {/snippet}
</Form>
