<script module lang="ts">
  import type { FormInputProps } from './FormInput.svelte'

  export type FormSecretInputProps = Omit<FormInputProps, 'type' | 'placeholder'> & {
    // A secret is stored: the field reads as filled, and left blank it keeps it.
    stored: boolean
    // Forgets the stored secret.
    removeUrl: string
    removedMessage: string
    // Id of the remove button; its confirmation takes `-confirm`.
    removeId: string
    onremoved: () => Promise<unknown>
  }
</script>

<script lang="ts">
  import { Button } from '$components/dsfr'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { FormInput } from '.'

  let {
    value = $bindable(),
    stored,
    removeUrl,
    removedMessage,
    removeId,
    onremoved,
    help,
    ...props
  }: FormSecretInputProps & { value: string } = $props()

  let confirming = $state(false)
  let removing = $state(false)

  async function remove() {
    removing = true
    try {
      await api.request(removeUrl, { method: 'delete' })
      confirming = false
      await onremoved()
      useToast(removedMessage, 5000, 'success')
    } catch (error) {
      useToast((error as Error).message, 6000, 'error')
    } finally {
      removing = false
    }
  }
</script>

<FormInput
  {...props}
  type="password"
  placeholder={stored ? '• '.repeat(20) : undefined}
  help={stored ? m['admin.endpointKey.hint']() : help}
  bind:value
>
  {#if stored}
    {#if confirming}
      <Button
        id="{removeId}-confirm"
        variant="secondary"
        text={m['admin.endpointKey.removeConfirm']()}
        disabled={removing}
        class="text-nowrap"
        onclick={remove}
      />
      <Button text={m['words.back']()} disabled={removing} onclick={() => (confirming = false)} />
    {:else}
      <Button
        id={removeId}
        icon="delete-bin-line"
        text={m['admin.endpointKey.remove']()}
        class="text-nowrap"
        onclick={() => (confirming = true)}
      />
    {/if}
  {/if}
</FormInput>
