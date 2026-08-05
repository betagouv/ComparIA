<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { getAuthContext } from '$lib/auth.svelte'
  import { Badge, Button, Icon, Input, Modal, Select, Table } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { api, type ApiError } from '$lib/fastapi-client'
  import type { AdminVoteTag } from '$lib/generated/admin'
  import { getLocales } from '$lib/global.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { TableCol } from '$lib/utils/data'
  import type { VoteTagSign } from '$lib/voteTags'
  import type { PageData } from './$types'

  let { data }: { data: PageData } = $props()

  const auth = getAuthContext()
  const refetch = () => invalidate('admin:vote-tags')

  // The default locale mints the published key, so its field comes first and
  // carries the hint, and its label is the one the lists show. Only the
  // locales the instance actually serves, same set as the language switcher.
  const defaultLocale = $derived(data.defaultLocale)
  const orderedLocales = $derived(
    getLocales(auth.config.enabled_locales).sort(
      (left, right) =>
        Number(right.code === defaultLocale) - Number(left.code === defaultLocale)
    )
  )

  // A reorder shows up here first and the request only confirms it, so moving
  // three tags is three clicks rather than three round trips. Cleared as soon
  // as the server answers, which makes its order the one on screen again.
  let optimistic = $state<AdminVoteTag[]>()
  let moveSeq = 0
  let announcement = $state('')
  const tags = $derived(optimistic ?? data.voteTags.tags)

  const signs: VoteTagSign[] = ['positive', 'negative']
  const bySign = $derived({
    positive: tags.filter((tag) => tag.sign === 'positive'),
    negative: tags.filter((tag) => tag.sign === 'negative')
  })

  const cols = [
    { id: 'order', label: m['admin.voteTags.colOrder']() },
    { id: 'label', label: m['admin.voteTags.colLabel']() },
    { id: 'key', label: m['admin.voteTags.colKey']() },
    { id: 'status', label: m['admin.voteTags.colStatus']() },
    { id: 'usage_count', label: m['admin.voteTags.colUsage']() },
    { id: 'actions', label: m['admin.voteTags.colActions']() }
  ] satisfies TableCol[]

  let busy = $state(false)
  let formError = $state<string>()
  let editing = $state<AdminVoteTag>()
  let tagToDelete = $state<AdminVoteTag>()

  let formSign = $state<VoteTagSign>('positive')
  let formEmoji = $state('')
  let formLabels = $state<Record<string, string>>({})

  // The key comes from the first label the admin fills in and never changes
  // afterwards, so it is worth showing before they commit to it.
  const keyPreview = $derived(
    (formLabels[defaultLocale] || Object.values(formLabels).find(Boolean) || '')
      .normalize('NFKD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 100)
  )

  function discloseModal(id: string) {
    const element = document.getElementById(id)
    // @ts-expect-error - DSFR is globally available
    if (element) window.dsfr(element).modal.disclose()
  }

  function closeModal(id: string) {
    const element = document.getElementById(id)
    // @ts-expect-error - DSFR is globally available
    if (element) window.dsfr(element).modal.conceal()
  }

  function openAdd(sign: VoteTagSign) {
    editing = undefined
    formSign = sign
    formEmoji = ''
    formLabels = {}
    formError = undefined
    discloseModal('fr-modal-vote-tag')
  }

  function openEdit(tag: AdminVoteTag) {
    editing = tag
    formSign = tag.sign
    formEmoji = tag.emoji
    formLabels = { ...(tag.labels ?? {}) }
    formError = undefined
    discloseModal('fr-modal-vote-tag')
  }

  function openDelete(tag: AdminVoteTag) {
    tagToDelete = tag
    discloseModal('fr-modal-vote-tag-delete')
  }

  async function run(action: () => Promise<unknown>, success: string) {
    busy = true
    formError = undefined
    try {
      await action()
      useToast(success, 4000)
      await refetch()
      optimistic = undefined
      return true
    } catch (error) {
      const { status, message } = error as ApiError
      formError =
        status === 409
          ? m['admin.voteTags.conflictError']()
          : status === 422
            ? m['admin.voteTags.labelError']()
            : message
      useToast(formError, 6000, 'error')
      return false
    } finally {
      busy = false
    }
  }

  async function submit(event: SubmitEvent) {
    event.preventDefault()

    // Ordered, because the backend mints the key from the first label it gets.
    const labels = Object.fromEntries(
      orderedLocales
        .map(({ code }) => [code, (formLabels[code] ?? '').trim()])
        .filter(([, value]) => value)
    )
    const emoji = formEmoji.trim()
    if (!emoji || !Object.keys(labels).length) {
      formError = m['admin.voteTags.labelError']()
      return
    }
    // Mirrors the backend check. The chip in the arena is one character wide,
    // so a word typed in here breaks its layout.
    if (!/^[\p{Extended_Pictographic}\p{Emoji_Component}]+$/u.test(emoji)) {
      formError = m['admin.voteTags.emojiError']()
      return
    }

    const target = editing
    const done = await run(
      () =>
        target
          ? api.request(`/admin/vote-tags/${target.id}`, {
              method: 'PUT',
              body: JSON.stringify({ emoji, labels })
            })
          : api.request('/admin/vote-tags', {
              method: 'POST',
              body: JSON.stringify({ sign: formSign, emoji, labels })
            }),
      target ? m['admin.voteTags.editSuccess']() : m['admin.voteTags.createSuccess']()
    )
    if (done) closeModal('fr-modal-vote-tag')
  }

  async function reorder(sign: VoteTagSign, from: number, to: number) {
    const side = bySign[sign]
    if (from === to || to < 0 || to >= side.length) return

    const reordered = [...side]
    reordered.splice(to, 0, ...reordered.splice(from, 1))
    // A row that moves under the pointer needs saying out loud for anyone
    // driving this from the keyboard.
    announcement = m['admin.voteTags.moved']({
      label: displayLabel(side[from]),
      position: to + 1,
      total: side.length
    })
    // No 'busy' here: the point is that the next move lands straight away.
    optimistic = [...reordered, ...tags.filter((tag) => tag.sign !== sign)]
    // Moving again before the last request answers would otherwise let the
    // older one drop the newer order on the floor.
    const seq = ++moveSeq

    try {
      await api.request('/admin/vote-tags/order', {
        method: 'PUT',
        body: JSON.stringify({ sign, ids: reordered.map((tag) => tag.id) })
      })
    } catch (error) {
      useToast((error as ApiError).message, 6000, 'error')
    }
    await refetch()
    if (seq === moveSeq) optimistic = undefined
  }

  function move(tag: AdminVoteTag, direction: 'up' | 'down') {
    const from = bySign[tag.sign].findIndex((other) => other.id === tag.id)
    return reorder(tag.sign, from, direction === 'up' ? from - 1 : from + 1)
  }

  // Dragging is the shortcut; the up and down buttons stay because a drag is
  // not reachable from a keyboard.
  let dragging = $state<{ sign: VoteTagSign; index: number }>()
  let dropTarget = $state<{ sign: VoteTagSign; index: number }>()

  function onDragStart(event: DragEvent, sign: VoteTagSign, index: number) {
    dragging = { sign, index }
    event.dataTransfer?.setData('text/plain', String(index))
    if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
  }

  function onDragOver(event: DragEvent, sign: VoteTagSign, index: number) {
    // A tag only ever moves within its own side, so a drag across the two
    // tables is refused rather than silently changing the tag's sign.
    if (dragging?.sign !== sign) return
    event.preventDefault()
    dropTarget = { sign, index }
  }

  function onDrop(event: DragEvent, sign: VoteTagSign, index: number) {
    event.preventDefault()
    const source = dragging
    dragging = undefined
    dropTarget = undefined
    if (source?.sign !== sign) return
    reorder(sign, source.index, index)
  }

  const setArchived = (tag: AdminVoteTag, archived: boolean) =>
    run(
      () =>
        api.request(`/admin/vote-tags/${tag.id}`, {
          method: 'PATCH',
          body: JSON.stringify({ archived })
        }),
      archived ? m['admin.voteTags.archiveSuccess']() : m['admin.voteTags.restoreSuccess']()
    )

  async function confirmDelete() {
    if (!tagToDelete) return
    const done = await run(
      () => api.request(`/admin/vote-tags/${tagToDelete!.id}`, { method: 'DELETE' }),
      m['admin.voteTags.deleteSuccess']()
    )
    if (done) {
      closeModal('fr-modal-vote-tag-delete')
      tagToDelete = undefined
    }
  }

  function displayLabel(tag: AdminVoteTag) {
    if (!tag.reserved)
      return tag.labels?.[defaultLocale] ?? Object.values(tag.labels ?? {})[0] ?? ''
    return (m as unknown as Record<string, () => string>)[`vote.choices.${tag.sign}.${tag.key}`]()
  }
</script>

<PageLayout
  seoTitle={m['admin.voteTags.title']()}
  title={m['admin.voteTags.title']()}
  subtitle={m['admin.voteTags.subtitle']()}
>
  <p class="sr-only" aria-live="polite">{announcement}</p>

  {#each signs as sign (sign)}
    {@const tags = bySign[sign]}
    <section class="mb-10 last:mb-0">
      <Table
        caption={m[`admin.voteTags.${sign}`]()}
        hideCaption
        {cols}
        rows={tags}
        animateRows
        rowAttributes={(row, index) => ({
          draggable: true,
          class:
            dropTarget?.sign === sign && dropTarget.index === index
              ? 'bg-very-light-primary'
              : dragging?.sign === sign && dragging.index === index
                ? 'opacity-50'
                : undefined,
          ondragstart: (event: DragEvent) => onDragStart(event, sign, index),
          ondragover: (event: DragEvent) => onDragOver(event, sign, index),
          ondrop: (event: DragEvent) => onDrop(event, sign, index),
          ondragend: () => {
            dragging = undefined
            dropTarget = undefined
          }
        })}
      >
        {#snippet headerLeft()}
          <h2 class="fr-h6 mb-0!">{m[`admin.voteTags.${sign}`]()}</h2>
        {/snippet}

        {#snippet headerRight()}
          <Button
            text={m['admin.voteTags.addTitle']()}
            icon="add-line"
            variant="secondary"
            class="md:ms-auto"
            aria-controls="fr-modal-vote-tag"
            data-fr-opened="false"
            onclick={() => openAdd(sign)}
          />
        {/snippet}

        {#snippet cell(row, col)}
          {#if col.id === 'label'}
            <span class="gap-2 flex items-center">
              <span class="text-xl" aria-hidden="true">{row.emoji}</span>
              <strong class={{ 'text-grey line-through': row.archived }}>
                {displayLabel(row)}
              </strong>
            </span>
          {:else if col.id === 'key'}
            <code class="text-xs text-grey">{row.key}</code>
          {:else if col.id === 'status'}
            <span class="gap-1 flex flex-wrap">
              <Badge
                size="sm"
                text={row.archived
                  ? m['admin.voteTags.archived']()
                  : m['admin.voteTags.active']()}
                variant={row.archived ? 'orange' : 'green'}
              />
              {#if row.reserved}
                <Badge size="sm" text={m['admin.voteTags.reserved']()} />
              {/if}
            </span>
          {:else if col.id === 'usage_count'}
            <span class="fr-text--sm text-grey">{row.usage_count}</span>
          {:else if col.id === 'order'}
            <span class="gap-1 flex items-center">
              <Icon
                icon="i-ri-draggable"
                class="cursor-grab text-grey"
                aria-hidden="true"
                title={m['admin.voteTags.dragHint']()}
              />
              <Button
                size="sm"
                variant="tertiary-no-outline"
                icon="arrow-up-line"
                iconOnly
                text={m['admin.voteTags.moveUp']()}
                title={m['admin.voteTags.moveUp']()}
                disabled={busy || tags[0]?.id === row.id}
                onclick={() => move(row, 'up')}
              />
              <Button
                size="sm"
                variant="tertiary-no-outline"
                icon="arrow-down-line"
                iconOnly
                text={m['admin.voteTags.moveDown']()}
                title={m['admin.voteTags.moveDown']()}
                disabled={busy || tags[tags.length - 1]?.id === row.id}
                onclick={() => move(row, 'down')}
              />
            </span>
          {:else if col.id === 'actions'}
            <span class="gap-1 flex justify-end">
              {#if !row.reserved}
                <Button
                  size="sm"
                  variant="tertiary-no-outline"
                  iconOnly
                  title={m['admin.voteTags.edit']()}
                  aria-label={`${m['admin.voteTags.edit']()} : ${displayLabel(row)}`}
                  disabled={busy}
                  aria-controls="fr-modal-vote-tag"
                  data-fr-opened="false"
                  onclick={() => openEdit(row)}
                >
                  <Icon icon="i-ri-edit-line" />
                </Button>
              {/if}
              <Button
                size="sm"
                variant="tertiary-no-outline"
                iconOnly
                title={row.archived
                  ? m['admin.voteTags.restore']()
                  : m['admin.voteTags.archive']()}
                aria-label={`${row.archived ? m['admin.voteTags.restore']() : m['admin.voteTags.archive']()} : ${displayLabel(row)}`}
                disabled={busy}
                onclick={() => setArchived(row, !row.archived)}
              >
                <Icon icon={row.archived ? 'i-ri-eye-line' : 'i-ri-eye-off-line'} />
              </Button>
              {#if !row.reserved && row.usage_count === 0}
                <Button
                  size="sm"
                  variant="tertiary-no-outline"
                  iconOnly
                  class="text-[--text-default-error]!"
                  title={m['admin.voteTags.delete']()}
                  aria-label={`${m['admin.voteTags.delete']()} : ${displayLabel(row)}`}
                  disabled={busy}
                  aria-controls="fr-modal-vote-tag-delete"
                  data-fr-opened="false"
                  onclick={() => openDelete(row)}
                >
                  <Icon icon="i-ri-delete-bin-line" />
                </Button>
              {/if}
            </span>
          {/if}
        {/snippet}
      </Table>

      {#if !tags.some((tag) => !tag.archived)}
        <p class="fr-text--sm mt-2! text-warning">{m['admin.voteTags.emptySide']()}</p>
      {/if}
    </section>
  {/each}
</PageLayout>

<Modal
  id="fr-modal-vote-tag"
  titleId="fr-modal-title-vote-tag"
  headerClass="md:absolute! md:top-4 md:right-8 md:z-10 md:p-0!"
  contentClass="md:pt-4! mb-6!"
>
  <h2 id="fr-modal-title-vote-tag" class="fr-modal__title">
    {editing ? m['admin.voteTags.editTitle']() : m['admin.voteTags.addTitle']()}
  </h2>

  <form onsubmit={submit}>
    {#if !editing}
      <Select
        id="vote-tag-sign"
        bind:selected={formSign}
        label={m['admin.voteTags.signLabel']()}
        options={signs.map((value) => ({ value, label: m[`admin.voteTags.${value}`]() }))}
      />
    {/if}

    <Input
      id="vote-tag-emoji"
      bind:value={formEmoji}
      label={m['admin.voteTags.emojiLabel']()}
      help={m['admin.voteTags.emojiHelp']()}
      maxlength={16}
    />

    {#each orderedLocales as locale (locale.code)}
      <Input
        id="vote-tag-label-{locale.code}"
        value={formLabels[locale.code] ?? ''}
        oninput={(event) =>
          (formLabels = { ...formLabels, [locale.code]: event.currentTarget.value })}
        label={m['admin.voteTags.labelFor']({ locale: locale.long })}
        help={locale.code === defaultLocale ? m['admin.voteTags.labelHelp']() : undefined}
        maxlength={100}
      />
    {/each}

    {#if editing}
      <p class="fr-text--sm text-grey">{m['admin.voteTags.keyFrozen']({ key: editing.key })}</p>
    {:else if keyPreview}
      <p class="fr-text--sm text-grey">{m['admin.voteTags.keyPreview']({ key: keyPreview })}</p>
    {/if}

    {#if formError}
      <p class="fr-error-text" aria-live="polite">{formError}</p>
    {/if}

    <div class="mt-6 gap-4 sm:flex-row sm:justify-end flex flex-col-reverse">
      <Button
        type="button"
        variant="secondary"
        text={m['admin.voteTags.cancel']()}
        onclick={() => closeModal('fr-modal-vote-tag')}
      />
      <Button
        type="submit"
        disabled={busy}
        text={editing ? m['admin.voteTags.save']() : m['admin.voteTags.addTitle']()}
      />
    </div>
  </form>
</Modal>

<Modal
  id="fr-modal-vote-tag-delete"
  titleId="fr-modal-title-vote-tag-delete"
  headerClass="md:absolute! md:top-4 md:right-8 md:z-10 md:p-0!"
  contentClass="md:pt-4! mb-6!"
>
  <h2 id="fr-modal-title-vote-tag-delete" class="fr-modal__title">
    {m['admin.voteTags.deleteConfirm']({ label: tagToDelete ? displayLabel(tagToDelete) : '' })}
  </h2>
  <p>{m['admin.voteTags.deleteWarning']()}</p>

  <div class="mt-6 gap-4 sm:flex-row sm:justify-end flex flex-col-reverse">
    <Button
      variant="secondary"
      text={m['admin.voteTags.cancel']()}
      disabled={busy}
      onclick={() => closeModal('fr-modal-vote-tag-delete')}
    />
    <Button text={m['admin.voteTags.delete']()} disabled={busy} onclick={confirmDelete} />
  </div>
</Modal>
