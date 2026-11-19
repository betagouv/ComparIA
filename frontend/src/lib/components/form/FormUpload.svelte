<script module lang="ts">
  export type FormUploadProps = BaseFormFieldProps<'upload'>
</script>

<script lang="ts">
  import { Button } from '$components/dsfr'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'

  import type { BaseFormFieldProps } from '$lib/utils/form'
  import FormField from './FormField.svelte'

  let {
    value = $bindable(),
    current,
    accept,
    disabled,
    onUpdate,
    ...props
  }: Omit<FormUploadProps, 'component'> & {
    value?: File | null
    current?: string | null
    accept?: string
    onUpdate?: (file: File | null) => void
  } = $props()

  function setFile(files: FileList | null) {
    value = files?.[0] ?? null
    onUpdate?.(value)
  }

  function removeFile() {
    value = null
    onUpdate?.(null)
  }

  let fileInput: HTMLInputElement

  function openFilePicker() {
    fileInput.click()
  }
</script>

<!-- FIXME component="upload" not working? -->
<FormField {...props} component="input">
  {#snippet formItem({ ...fieldProps })}
    <div class="mt-1 gap-2 flex items-start">
      {#if current}
        <img
          src={api.getPublicUrl(current)}
          class={['h-10 w-10 object-contain']}
          alt={m['form.upload.current']()}
        />
      {/if}
      <input
        {...fieldProps}
        {disabled}
        type="file"
        {accept}
        class="sr-only"
        bind:this={fileInput}
        onchange={(event) => setFile(event.currentTarget.files)}
      />
      <Button text={m['form.upload.browse']()} {disabled} onclick={openFilePicker} />
      {#if value}
        <span class="place-self-center truncate">{value.name}</span>
      {/if}
      {#if current || value}
        <Button
          text={m['form.upload.remove']()}
          {disabled}
          onclick={removeFile}
          variant="secondary"
        />
      {/if}
    </div>
  {/snippet}
</FormField>
