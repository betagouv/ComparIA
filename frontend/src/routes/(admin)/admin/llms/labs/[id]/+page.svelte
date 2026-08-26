<script lang="ts">
  import { goto, invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import AILogo from '$components/AILogo.svelte'
  import { Button } from '$components/dsfr'
  import Form from '$components/form/Form.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { useForm } from '$lib/stores/form.svelte'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()

  const id = $derived(page.params.id)
  const method = $derived(id === 'create' ? 'post' : 'put')
  let uploadingLogo = $state(false)
  let logoVersion = $state(0)
  let hasCustomLogo = $state(data.formProps.data.has_custom_logo)
  const form = $derived(
    useForm({
      url: '/admin/llms/lab',
      ...data.formProps,
      omitKeys: ['updated_at', 'created_at'],
      i18nKey: 'lab_upsert',
      method,
      onSuccess: async (updated) => {
        await invalidate('admin:llms')
        if (method === 'post') {
          await goto(resolve(`/admin/llms/labs/${updated.id}`))
        }
      }
    })
  )

  async function uploadLogo(event: Event) {
    const input = event.currentTarget as HTMLInputElement
    const file = input.files?.[0]
    if (!file || !data.formProps.data.id) return
    uploadingLogo = true
    try {
      const body = new FormData()
      body.append('file', file)
      const updated = await api.request<typeof data.formProps.data>(
        `/admin/llms/lab/${data.formProps.data.id}/logo`,
        { method: 'PUT', body, headers: {} }
      )
      Object.assign(data.formProps.data, updated)
      hasCustomLogo = true
      logoVersion++
      useToast('Logo updated', 4000)
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      uploadingLogo = false
      input.value = ''
    }
  }

  async function removeLogo() {
    if (!data.formProps.data.id) return
    uploadingLogo = true
    try {
      const updated = await api.request<typeof data.formProps.data>(
        `/admin/llms/lab/${data.formProps.data.id}/logo`,
        { method: 'DELETE' }
      )
      Object.assign(data.formProps.data, updated)
      hasCustomLogo = false
      useToast('Custom logo removed', 4000)
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      uploadingLogo = false
    }
  }
</script>

<div>
  <Form {id} label="Lab" subLabel={id} {...form} />
  {#if id !== 'create' && data.formProps.data.id}
    <section class="mt-6! p-6 cg-border max-w-[700px]">
      <h2 class="text-xl!">Custom logo</h2>
      <div class="gap-4 flex items-center">
        <AILogo
          logo={data.formProps.data.logo}
          customLogoId={hasCustomLogo ? data.formProps.data.id : undefined}
          customLogoVersion={logoVersion}
          size="lg"
          alt={data.formProps.data.name}
        />
        <label class="fr-label">
          <span class="fr-sr-only">Choose a logo file</span>
          <input
            type="file"
            accept="image/png,image/jpeg,image/svg+xml,image/webp"
            disabled={uploadingLogo}
            onchange={uploadLogo}
          />
        </label>
        {#if hasCustomLogo}
          <Button
            type="button"
            variant="secondary"
            size="sm"
            text="Remove custom logo"
            disabled={uploadingLogo}
            onclick={removeLogo}
          />
        {/if}
      </div>
      <p class="fr-hint-text mt-2!">PNG, JPEG, SVG or WebP, up to 2 MB.</p>
    </section>
  {/if}
</div>
