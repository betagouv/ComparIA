<script lang="ts">
  import { invalidateAll } from '$app/navigation'
  import { page } from '$app/state'
  import { Alert, Button, Checkbox } from '$components/dsfr'
  import { FormInput, type FormInputProps } from '$components/form'
  import AnyFormItem from '$components/form/AnyFormItem.svelte'
  import Form from '$components/form/Form.svelte'
  import { api } from '$lib/fastapi-client'
  import type { ToolAdmin, ToolUpsert } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { useForm } from '$lib/stores/form.svelte'
  import type { PageProps } from './$types'

  type ToolTestResult = {
    ok: boolean
    error: keyof typeof testErrors | null
    functions: { name: string; description: string }[] | null
  }

  const testErrors = {
    no_credential: m['admin.tools.errors.no_credential'],
    no_url: m['admin.tools.errors.no_url'],
    invalid_credential: m['admin.tools.errors.invalid_credential'],
    no_credit: m['admin.tools.errors.no_credit'],
    unreachable: m['admin.tools.errors.unreachable'],
    timeout: m['admin.tools.errors.timeout'],
    unknown_builtin: m['admin.tools.errors.unknown_builtin']
  }

  const { data }: PageProps = $props()

  const id = $derived(page.params.id)
  const hasSecret = $derived(!!(data.formProps.data as ToolAdmin).has_secret)

  let confirmingRemoval = $state(false)
  let removing = $state(false)
  let testing = $state(false)
  let testResult = $state<ToolTestResult>()

  const form = $derived(
    useForm({
      url: '/admin/tools/tool',
      ...data.formProps,
      omitKeys: ['updated_at', 'created_at', 'has_secret'],
      i18nKey: 'tool_upsert',
      method: 'put',
      // Reloaded rather than patched: the credential typed in is dropped
      // from the form, and whether one is now set comes from the server.
      onSuccess: () => invalidateAll()
    })
  )

  const values = $derived(form.form as Partial<ToolUpsert>)
  const isMcp = $derived(values.kind === 'mcp')
  const isWebSearch = $derived(values.kind !== 'mcp' && values.key === 'web_search')

  function field(fieldId: string) {
    return form.items.find((item) => item.id === fieldId)!
  }

  const secretField = $derived.by(() => {
    const help = isMcp ? m['admin.tools.secretHintMcp']() : m['admin.tools.secretHintBuiltin']()
    return {
      ...field('secret'),
      help,
      ...(hasSecret ? { placeholder: '• '.repeat(20) } : {})
    } as FormInputProps
  })

  // What the server listed, plus what is saved as allowed: before a test, the
  // saved list is all there is, and unticking an entry must not make it
  // vanish. A function the server dropped can still be unticked this way.
  const functionNames = $derived.by(() => {
    const listed = testResult?.functions?.map((f) => f.name) ?? []
    const saved = (data.formProps.data as ToolAdmin).allowed_functions ?? []
    return [...new Set([...listed, ...saved, ...(values.allowed_functions ?? [])])]
  })

  // Servers write their descriptions for models, at length. The first
  // sentence is enough to choose by.
  function describe(name: string) {
    const description = testResult?.functions?.find((f) => f.name === name)?.description ?? ''
    return description.split(/(?<=\.)\s/)[0]
  }

  function toggleFunction(name: string, checked: boolean) {
    const others = (values.allowed_functions ?? []).filter((n) => n !== name)
    const next = checked ? [...others, name] : others
    form.form.allowed_functions = next.length ? next : null
  }

  async function removeSecret() {
    removing = true
    try {
      await api.request(`/admin/tools/tool/${id}/secret`, { method: 'delete' })
      confirmingRemoval = false
      await invalidateAll()
      useToast(m['admin.tools.removed'](), 5000, 'success')
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      removing = false
    }
  }

  async function runTest() {
    testing = true
    testResult = undefined
    try {
      testResult = await api.request<ToolTestResult>(`/admin/tools/tool/${id}/test`, {
        method: 'post'
      })
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      testing = false
    }
  }
</script>

<div>
  {#snippet secret()}
    <FormInput {...secretField} type="password" bind:value={form.form['secret']!}>
      {#if hasSecret}
        {#if confirmingRemoval}
          <Button
            id="tool-secret-remove-confirm"
            variant="secondary"
            text={m['admin.tools.removeConfirm']()}
            disabled={removing}
            class="text-nowrap"
            onclick={removeSecret}
          />
          <Button
            text={m['words.back']()}
            disabled={removing}
            onclick={() => (confirmingRemoval = false)}
          />
        {:else}
          <Button
            id="tool-secret-remove"
            icon="delete-bin-line"
            text={m['admin.tools.remove']()}
            class="text-nowrap"
            onclick={() => (confirmingRemoval = true)}
          />
        {/if}
      {/if}
    </FormInput>
  {/snippet}

  {#snippet url()}
    {#if isMcp}
      <AnyFormItem {...field('url')} bind:value={form.form['url']!} errors={form.errors} />
    {/if}
  {/snippet}

  {#snippet allowedFunctions()}
    {#if isMcp}
      <fieldset class="fr-fieldset" aria-describedby="tool-functions-hint">
        <legend class="fr-fieldset__legend--regular fr-fieldset__legend">
          {m['admin.tools.functionsLegend']()}
          <span id="tool-functions-hint" class="fr-hint-text">
            {functionNames.length
              ? m['admin.tools.functionsHint']()
              : m['admin.tools.functionsUntested']()}
          </span>
        </legend>
        {#each functionNames as name (name)}
          <div class="fr-fieldset__element">
            <Checkbox
              id="tool-function-{name}"
              label={name}
              help={describe(name)}
              bind:checked={
                () => values.allowed_functions?.includes(name) ?? false,
                (checked) => toggleFunction(name, checked)
              }
            />
          </div>
        {/each}
      </fieldset>
    {/if}
  {/snippet}

  {#snippet allowedDomains()}
    {#if isWebSearch}
      <AnyFormItem
        {...field('allowed_domains')}
        bind:value={form.form['allowed_domains']!}
        errors={form.errors}
      />
    {/if}
  {/snippet}

  {#snippet blockedDomains()}
    {#if isWebSearch}
      <AnyFormItem
        {...field('blocked_domains')}
        bind:value={form.form['blocked_domains']!}
        errors={form.errors}
      />
    {/if}
  {/snippet}

  <Form
    {id}
    label="Tool"
    subLabel={id}
    {...form}
    fieldSnippets={{
      secret,
      url,
      allowed_functions: allowedFunctions,
      allowed_domains: allowedDomains,
      blocked_domains: blockedDomains
    }}
  />

  <section class="mt-6! p-6 cg-border max-w-[700px]" aria-labelledby="tool-test-title">
    <h2 id="tool-test-title" class="text-xl!">{m['admin.tools.test']()}</h2>
    <p class="fr-hint-text">{m['admin.tools.testHint']()}</p>
    <Button
      id="tool-test"
      icon="flashlight-line"
      variant="secondary"
      text={testing ? m['admin.tools.testing']() : m['admin.tools.test']()}
      disabled={testing}
      onclick={runTest}
    />
    <div aria-live="polite" class="mt-4">
      {#if testResult?.ok}
        <Alert
          small
          variant="success"
          title={testResult.functions
            ? m['admin.tools.testOkFunctions']({ count: testResult.functions.length })
            : m['admin.tools.testOk']()}
        />
      {:else if testResult}
        <Alert variant="error" title={m['admin.tools.testFailed']()}>
          <p>{testResult.error ? testErrors[testResult.error]() : ''}</p>
        </Alert>
      {/if}
    </div>
  </section>
</div>
