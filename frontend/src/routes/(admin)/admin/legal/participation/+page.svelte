<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import LegalPresentationPreview from '$components/admin/LegalPresentationPreview.svelte'
  import { Button, Textarea } from '$components/dsfr'
  import Form from '$components/form/Form.svelte'
  import FormTranslate from '$components/form/FormTranslate.svelte'
  import { PageLayout } from '$components/layout'
  import { getAuthContext } from '$lib/authContext.svelte'
  import type { ArenaLegalPresentation, SignInLegalPresentation } from '$lib/generated/admin'
  import { getLocales } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { useForm } from '$lib/stores/form.svelte'
  import { getKeys } from '$lib/utils/commons'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()

  const auth = getAuthContext()
  const locales = $derived(getLocales(auth.config.enabled_locales))

  const form = useForm({
    url: '/admin/legal/presentation',
    method: 'put',
    initialData: () => {
      const presentations = structuredClone(data.presentations)
      const currentLocales = getKeys(presentations)
      const missingLocales = locales.filter((locale) => !currentLocales.includes(locale.code))
      missingLocales.forEach((locale) => {
        presentations[locale.code] = {
          arena: {} as ArenaLegalPresentation,
          sign_in: {} as SignInLegalPresentation
        }
      })
      return presentations
    },
    onBeforeSubmit: (form) => {
      getKeys(form).forEach((k) => {
        // We need to clear an empty locale
        if (!getKeys(form[k].arena).length && !getKeys(form[k].sign_in).length) {
          delete form[k]
        }
      })
      return form
    },
    onSuccess: async () => await invalidate('admin:participation')
  })

  function clearLocale(locale: string) {
    form.form[locale] = {
      arena: {} as ArenaLegalPresentation,
      sign_in: {} as SignInLegalPresentation
    }
    Object.keys(form.errors).forEach((k) => {
      if (k.startsWith(locale)) delete form.errors[k]
    })
  }

  function isValid(locale: string) {
    if (!form.form[locale]) return false
    const sections = Object.values(form.form[locale]) as object[]
    if (sections.length != 2 || sections.some((v) => Object.keys(v).length === 0)) return false
    return Object.values(sections[0]).length === 4 || Object.values(sections[2]).length === 1
  }
</script>

<PageLayout
  seoTitle={m['admin.legal.participation.title']()}
  title={m['admin.legal.participation.title']()}
  subtitle={m['admin.legal.participation.subtitle']()}
  noPadding
>
  <p class="mb-0! px-4! md:px-6! pt-6">
    <a class="fr-link fr-icon-arrow-left-line fr-link--icon-left" href={resolve('/admin/legal')}>
      {m['admin.legal.back']()}
    </a>
  </p>

  <Form id="journey" label={m['admin.legal.participation.formTitle']()} {...form} stickyFooter>
    <FormTranslate id="journey-form" bind:value={form.form} {isValid}>
      {#snippet subSnippet(locale)}
        <Button
          icon="delete-bin-line"
          text="Clear locale content"
          size="sm"
          class="ms-6"
          onclick={() => clearLocale(locale)}
        />

        <section aria-labelledby="arena-section-title" class="mt-6">
          <h3 id="arena-section-title" class="fr-h4">
            {m['admin.legal.participation.arenaTitle']()}
          </h3>
          <p>{m['admin.legal.participation.arenaDescription']()}</p>
          <div class="fr-grid-row fr-grid-row--gutters">
            <div class="fr-col-12 fr-col-lg-7">
              <Textarea
                id="{locale}-arena-title"
                label={m['admin.legal.participation.modalTitle']()}
                rows={2}
                maxlength={200}
                required
                error={form.errors[`${locale}-arena-title`]}
                bind:value={form.form[locale].arena.title}
              />
              <Textarea
                id="{locale}-arena-introduction"
                label={m['admin.legal.participation.introduction']()}
                help={m['admin.legal.markdownHelp']()}
                groupClass="fr-mt-4v"
                rows={4}
                maxlength={2000}
                required
                error={form.errors[`${locale}-arena-introduction`]}
                bind:value={form.form[locale].arena.introduction}
              />
              <Textarea
                id="{locale}-arena-checkbox_label"
                label={m['admin.legal.participation.checkboxLabel']()}
                help={m['admin.legal.markdownHelp']()}
                groupClass="fr-mt-4v"
                rows={5}
                maxlength={2000}
                required
                error={form.errors[`${locale}-arena-checkbox_label`]}
                bind:value={form.form[locale].arena.checkbox_label}
              />
              <Textarea
                id="{locale}-arena-button_label"
                label={m['admin.legal.participation.buttonLabel']()}
                groupClass="fr-mt-4v"
                rows={2}
                maxlength={200}
                error={form.errors[`${locale}-arena-button_label`]}
                bind:value={form.form[locale].arena.button_label}
              />
            </div>
            <div class="fr-col-12 fr-col-lg-5">
              <LegalPresentationPreview kind="arena" {...form.form[locale].arena} />
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
                id="{locale}-sign_in-checkbox_label"
                label={m['admin.legal.participation.checkboxLabel']()}
                help={m['admin.legal.markdownHelp']()}
                rows={5}
                maxlength={2000}
                required
                error={form.errors[`${locale}-sign_in-checkbox_label`]}
                bind:value={form.form[locale].sign_in.checkbox_label}
              />
            </div>
            <div class="fr-col-12 fr-col-lg-5">
              <LegalPresentationPreview
                kind="sign-in"
                checkbox_label={form.form[locale].sign_in.checkbox_label}
              />
            </div>
          </div>
        </section>
      {/snippet}
    </FormTranslate>
  </Form>
</PageLayout>
