<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Alert, Badge, Button, Icon, Modal, Table, Toggle } from '$components/dsfr'
  import Link from '$components/dsfr/Link.svelte'
  import { api } from '$lib/fastapi-client'
  import type { SelectionModeAdmin } from '$lib/generated/admin'
  import { getLocalesContext } from '$lib/global.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { TableCol } from '$lib/utils/data'
  import { tick } from 'svelte'
  import { requestErrorText } from './errors'
  import { modeLabel, openToEveryone, toForm, toUpsert } from './mode'
  import { blockedByTools, ruleSummary, warningText } from './summary'
  import type { PageProps } from './$types'

  let { data }: PageProps = $props()
  const locales = getLocalesContext()
  const baseRoute = '/admin/modes-selection' as const
  const refetch = () => invalidate('admin:selection-modes')

  // A move shows up straight away and the request only confirms it, as on
  // the vote tags page.
  let optimistic = $state<SelectionModeAdmin[]>()
  let moveSeq = 0
  let announcement = $state('')
  const modes = $derived((optimistic ?? data.modes).map((mode) => ({ ...mode, id: mode.id! })))

  const cols = [
    { id: 'order', label: m['admin.selectionModes.list.order']() },
    { id: 'label', label: m['admin.selectionModes.list.mode']() },
    { id: 'rule', label: m['admin.selectionModes.list.rule']() },
    { id: 'enabled', label: m['admin.selectionModes.list.enabled']() },
    { id: 'actions', label: m['admin.selectionModes.list.actions']() }
  ] satisfies TableCol[]

  const labelOf = (mode: SelectionModeAdmin) => modeLabel(mode, locales)

  function toolLabel(key: string) {
    return data.tools.find((tool) => tool.key === key)?.label ?? key
  }

  async function reorder(from: number, to: number) {
    if (from === to || to < 0 || to >= modes.length) return
    const reordered = [...modes]
    reordered.splice(to, 0, ...reordered.splice(from, 1))
    announcement = m['admin.selectionModes.list.moved']({
      label: labelOf(modes[from]),
      position: to + 1,
      total: modes.length
    })
    optimistic = reordered
    const seq = ++moveSeq
    try {
      await api.request('/admin/selection-modes/reorder', {
        method: 'POST',
        body: JSON.stringify({ ids: reordered.map((mode) => mode.id) })
      })
    } catch (error) {
      useToast(requestErrorText(error), 6000, 'error')
    }
    await refetch()
    if (seq === moveSeq) optimistic = undefined
  }

  async function move(mode: SelectionModeAdmin, step: -1 | 1) {
    const from = modes.findIndex((other) => other.id === mode.id)
    const to = from + step
    const atEnd = to === 0 || to === modes.length - 1
    const done = reorder(from, to)
    // Moving the row moves its nodes, which drops focus: it goes back to the
    // arrow just pressed, or to the other one when the row reached an end and
    // the pressed one is disabled. Again once the list has reloaded.
    const keepFocus = () => {
      const pressed = step < 0 ? 'up' : 'down'
      const other = step < 0 ? 'down' : 'up'
      document.getElementById(`mode-${atEnd ? other : pressed}-${mode.id}`)?.focus()
    }
    await tick()
    keepFocus()
    await done
    await tick()
    if (document.activeElement === document.body) keepFocus()
  }

  // What the switch shows while its request is out, so it moves on click.
  let pending = $state<Record<string, boolean>>({})

  async function setEnabled(mode: SelectionModeAdmin, enabled: boolean) {
    pending[mode.id!] = enabled
    try {
      await api.request(`/admin/selection-modes/${mode.id}`, {
        method: 'PUT',
        body: JSON.stringify(toUpsert({ ...toForm(mode), enabled }))
      })
      await refetch()
      useToast(
        enabled
          ? m['admin.selectionModes.list.switchedOn']({ label: labelOf(mode) })
          : m['admin.selectionModes.list.switchedOff']({ label: labelOf(mode) }),
        4000,
        'success'
      )
    } catch (error) {
      useToast(requestErrorText(error), 8000, 'error')
    } finally {
      delete pending[mode.id!]
    }
  }

  let toDelete = $state<SelectionModeAdmin>()
  let deleting = $state(false)
  let deleteError = $state<string>()

  function modal(action: 'disclose' | 'conceal') {
    const element = document.getElementById('fr-modal-mode-delete')
    // @ts-expect-error - DSFR is globally available
    if (element) window.dsfr(element).modal[action]()
  }

  function askDelete(mode: SelectionModeAdmin) {
    toDelete = mode
    deleteError = undefined
    modal('disclose')
  }

  async function confirmDelete() {
    if (!toDelete) return
    deleting = true
    deleteError = undefined
    const label = labelOf(toDelete)
    try {
      await api.request(`/admin/selection-modes/${toDelete.id}`, { method: 'DELETE' })
      modal('conceal')
      toDelete = undefined
      await refetch()
      useToast(m['admin.selectionModes.list.deleted']({ label }), 5000, 'success')
    } catch (error) {
      deleteError = requestErrorText(error)
    } finally {
      deleting = false
    }
  }

  // Checked when the page loads: a window opening later shows on the next visit.
  const nobodyCovered = $derived(!modes.some((mode) => openToEveryone(mode)))

  function warningsOf(mode: SelectionModeAdmin) {
    const toolsBlock = blockedByTools(mode, mode.viability)
    return (mode.viability.warnings ?? []).map((warning) =>
      warningText(warning, !!mode.pool_b, toolsBlock)
    )
  }
</script>

<p class="mb-6! max-w-[700px] text-[--text-mention-grey]">
  {m['admin.selectionModes.list.intro']()}
</p>
<p class="sr-only" aria-live="polite">{announcement}</p>

{#if nobodyCovered}
  <Alert
    variant="warning"
    small
    class="mb-6"
    title={m['admin.selectionModes.list.nobodyCovered']()}
  />
{/if}

<Table caption={m['admin.selectionModes.title']()} hideCaption {cols} rows={modes} animateRows>
  {#snippet headerLeft()}
    <Link
      button
      icon="add-line"
      text={m['admin.selectionModes.list.add']()}
      href={resolve(`${baseRoute}/create`)}
    />
  {/snippet}

  {#snippet cell(mode, col)}
    {#if col.id === 'order'}
      <span class="gap-1 flex items-center">
        <Button
          id="mode-up-{mode.id}"
          size="sm"
          variant="tertiary-no-outline"
          icon="arrow-up-line"
          iconOnly
          text={m['admin.selectionModes.list.moveUp']({ label: labelOf(mode) })}
          title={m['admin.selectionModes.list.moveUp']({ label: labelOf(mode) })}
          disabled={modes[0]?.id === mode.id}
          onclick={() => move(mode, -1)}
        />
        <Button
          id="mode-down-{mode.id}"
          size="sm"
          variant="tertiary-no-outline"
          icon="arrow-down-line"
          iconOnly
          text={m['admin.selectionModes.list.moveDown']({ label: labelOf(mode) })}
          title={m['admin.selectionModes.list.moveDown']({ label: labelOf(mode) })}
          disabled={modes[modes.length - 1]?.id === mode.id}
          onclick={() => move(mode, 1)}
        />
      </span>
    {:else if col.id === 'label'}
      <span class="gap-3 flex items-start">
        <Icon
          icon={mode.icon}
          class="mt-1 shrink-0 text-[--text-action-high-blue-france]"
          aria-hidden="true"
        />
        <span class="min-w-0">
          <a href={resolve(`${baseRoute}/${mode.id}`)} class="font-bold">{labelOf(mode)}</a>
          <code class="text-xs block text-[--text-mention-grey]">{mode.key}</code>
          {#if mode.is_default}
            <Badge
              size="sm"
              variant="info"
              text={m['admin.selectionModes.list.default']()}
              class="mt-1"
            />
          {/if}
        </span>
      </span>
    {:else if col.id === 'rule'}
      <span class="fr-text--sm mb-0! block max-w-[28rem]">
        {ruleSummary(mode, mode.viability, toolLabel)}
      </span>
      {#if !mode.viability.viable}
        <Badge
          id="mode-warning-{mode.id}"
          size="sm"
          variant="red"
          class="mt-1"
          text={m['admin.selectionModes.list.notViable']()}
          tooltip={warningsOf(mode).join(' ')}
        />
      {:else if mode.viability.warnings?.length}
        <Badge
          id="mode-warning-{mode.id}"
          size="sm"
          variant="orange"
          class="mt-1"
          text={m['admin.selectionModes.list.check']()}
          tooltip={warningsOf(mode).join(' ')}
        />
      {/if}
    {:else if col.id === 'enabled'}
      <Toggle
        id="mode-enabled-{mode.id}"
        labelPos="right"
        bind:value={
          () => pending[mode.id] ?? mode.enabled ?? true, (value) => setEnabled(mode, value)
        }
      >
        <span class="fr-sr-only"
          >{m['admin.selectionModes.list.switch']({ label: labelOf(mode) })}</span
        >
      </Toggle>
    {:else if col.id === 'actions'}
      <span class="gap-1 flex justify-end">
        <Link
          href={resolve(`${baseRoute}/${mode.id}`)}
          button
          size="sm"
          variant="tertiary-no-outline"
          icon="edit-line"
          iconOnly
          text={m['admin.selectionModes.list.edit']({ label: labelOf(mode) })}
          title={m['admin.selectionModes.list.edit']({ label: labelOf(mode) })}
        />
        <Button
          size="sm"
          variant="tertiary-no-outline"
          icon="delete-bin-line"
          iconOnly
          class="text-[--text-default-error]!"
          text={m['admin.selectionModes.list.delete']({ label: labelOf(mode) })}
          title={m['admin.selectionModes.list.delete']({ label: labelOf(mode) })}
          aria-controls="fr-modal-mode-delete"
          data-fr-opened="false"
          onclick={() => askDelete(mode)}
        />
      </span>
    {/if}
  {/snippet}
</Table>

<Modal
  id="fr-modal-mode-delete"
  titleId="fr-modal-title-mode-delete"
  headerClass="md:absolute! md:top-4 md:right-8 md:z-10 md:p-0!"
  contentClass="md:pt-4! mb-6!"
>
  <h2 id="fr-modal-title-mode-delete" class="fr-modal__title">
    {m['admin.selectionModes.list.deleteTitle']({ label: toDelete ? labelOf(toDelete) : '' })}
  </h2>
  <p>{m['admin.selectionModes.list.deleteWarning']({ key: toDelete?.key ?? '' })}</p>
  <div aria-live="assertive">
    {#if deleteError}
      <p class="fr-message fr-message--error mb-4!">{deleteError}</p>
    {/if}
  </div>

  <div class="mt-6 gap-4 sm:flex-row sm:justify-end flex flex-col-reverse">
    <Button
      variant="secondary"
      text={m['words.cancel']()}
      disabled={deleting}
      onclick={() => modal('conceal')}
    />
    <Button
      icon="delete-bin-line"
      text={deleting
        ? m['admin.selectionModes.list.deleting']()
        : m['admin.selectionModes.list.confirmDelete']()}
      disabled={deleting}
      onclick={confirmDelete}
    />
  </div>
</Modal>
