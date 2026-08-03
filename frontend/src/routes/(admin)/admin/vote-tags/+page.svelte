<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Badge, Button, Input, Select } from '$components/dsfr'
  import { api, type ApiError } from '$lib/fastapi-client'
  import type { AdminVoteTag } from '$lib/generated/admin'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { baseLocale, locales } from '$lib/i18n/runtime'
  import type { VoteTagSign } from '$lib/voteTags'
  import type { PageData } from './$types'

  let { data }: { data: PageData } = $props()

  const refetch = () => invalidate('admin:vote-tags')

  const bySign = $derived({
    positive: data.voteTags.tags.filter((tag) => tag.sign === 'positive'),
    negative: data.voteTags.tags.filter((tag) => tag.sign === 'negative')
  })

  const signs: VoteTagSign[] = ['positive', 'negative']

  let busy = $state(false)
  let formError = $state<string>()
  let editing = $state<AdminVoteTag>()

  let newSign = $state<VoteTagSign>('positive')
  let newEmoji = $state('')
  let newLabels = $state<Record<string, string>>({})

  // The key comes from the first label the admin fills in and never changes
  // afterwards, so it is worth showing before they commit to it.
  const keyPreview = $derived(
    (newLabels[baseLocale] || Object.values(newLabels).find(Boolean) || '')
      .normalize('NFKD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 100)
  )

  function labelsPayload(source: Record<string, string>) {
    return Object.fromEntries(
      Object.entries(source)
        .map(([locale, value]) => [locale, value.trim()])
        .filter(([, value]) => value)
    )
  }

  async function run(action: () => Promise<unknown>, success: string) {
    busy = true
    formError = undefined
    try {
      await action()
      useToast(success, 4000)
      await refetch()
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

  async function create(event: SubmitEvent) {
    event.preventDefault()
    const labels = labelsPayload(newLabels)
    if (!newEmoji.trim() || !Object.keys(labels).length) {
      formError = m['admin.voteTags.labelError']()
      return
    }
    const done = await run(
      () =>
        api.request('/admin/vote-tags', {
          method: 'POST',
          body: JSON.stringify({ sign: newSign, emoji: newEmoji.trim(), labels })
        }),
      m['admin.voteTags.createSuccess']()
    )
    if (done) {
      newEmoji = ''
      newLabels = {}
    }
  }

  async function saveEdit(event: SubmitEvent) {
    event.preventDefault()
    if (!editing) return
    const labels = labelsPayload(editing.labels ?? {})
    if (!editing.emoji.trim() || !Object.keys(labels).length) {
      formError = m['admin.voteTags.labelError']()
      return
    }
    const target = editing
    const done = await run(
      () =>
        api.request(`/admin/vote-tags/${target.id}`, {
          method: 'PUT',
          body: JSON.stringify({ emoji: target.emoji.trim(), labels })
        }),
      m['admin.voteTags.editSuccess']()
    )
    if (done) editing = undefined
  }

  const move = (tag: AdminVoteTag, direction: 'up' | 'down') =>
    run(
      () =>
        api.request(`/admin/vote-tags/${tag.id}/move`, {
          method: 'POST',
          body: JSON.stringify({ direction })
        }),
      m['admin.voteTags.moveSuccess']()
    )

  const setArchived = (tag: AdminVoteTag, archived: boolean) =>
    run(
      () =>
        api.request(`/admin/vote-tags/${tag.id}`, {
          method: 'PATCH',
          body: JSON.stringify({ archived })
        }),
      archived ? m['admin.voteTags.archiveSuccess']() : m['admin.voteTags.restoreSuccess']()
    )

  const remove = (tag: AdminVoteTag) =>
    run(
      () => api.request(`/admin/vote-tags/${tag.id}`, { method: 'DELETE' }),
      m['admin.voteTags.deleteSuccess']()
    )

  function displayLabel(tag: AdminVoteTag) {
    if (!tag.reserved) return tag.labels?.[baseLocale] ?? Object.values(tag.labels ?? {})[0] ?? ''
    return (m as unknown as Record<string, () => string>)[`vote.choices.${tag.sign}.${tag.key}`]()
  }
</script>

<h1 class="fr-h3">{m['admin.voteTags.title']()}</h1>
<p class="fr-text--sm text-grey">{m['admin.voteTags.intro']()}</p>

{#each signs as sign (sign)}
  {@const tags = bySign[sign]}
  <section class="mt-8">
    <h2 class="fr-h5">{m[`admin.voteTags.${sign}`]()}</h2>

    {#if !tags.filter((tag) => !tag.archived).length}
      <p class="fr-text--sm text-warning">{m['admin.voteTags.emptySide']()}</p>
    {/if}

    <ul class="p-0 list-none">
      {#each tags as tag, index (tag.id)}
        <li class="cg-border gap-3 mb-2 px-3 py-2 rounded-lg flex items-center">
          <span class="text-xl" aria-hidden="true">{tag.emoji}</span>

          <span class="grow">
            <strong class={{ 'text-grey line-through': tag.archived }}>{displayLabel(tag)}</strong>
            <code class="ms-2 text-xs text-grey">{tag.key}</code>
          </span>

          {#if tag.reserved}
            <Badge text={m['admin.voteTags.reserved']()} />
          {/if}
          {#if tag.archived}
            <Badge text={m['admin.voteTags.archived']()} variant="orange" />
          {/if}
          <span class="text-xs text-grey">
            {m['admin.voteTags.usage']({ count: tag.usage_count })}
          </span>

          <Button
            size="sm"
            variant="tertiary"
            icon="arrow-up-line"
            iconOnly
            text={m['admin.voteTags.moveUp']()}
            title={m['admin.voteTags.moveUp']()}
            disabled={busy || index === 0}
            onclick={() => move(tag, 'up')}
          />
          <Button
            size="sm"
            variant="tertiary"
            icon="arrow-down-line"
            iconOnly
            text={m['admin.voteTags.moveDown']()}
            title={m['admin.voteTags.moveDown']()}
            disabled={busy || index === tags.length - 1}
            onclick={() => move(tag, 'down')}
          />
          {#if !tag.reserved}
            <Button
              size="sm"
              variant="tertiary"
              icon="edit-line"
              iconOnly
              text={m['admin.voteTags.edit']()}
              title={m['admin.voteTags.edit']()}
              disabled={busy}
              onclick={() => (editing = { ...tag, labels: { ...(tag.labels ?? {}) } })}
            />
          {/if}
          <Button
            size="sm"
            variant="tertiary"
            icon={tag.archived ? 'eye-line' : 'eye-off-line'}
            iconOnly
            text={tag.archived ? m['admin.voteTags.restore']() : m['admin.voteTags.archive']()}
            title={tag.archived ? m['admin.voteTags.restore']() : m['admin.voteTags.archive']()}
            disabled={busy}
            onclick={() => setArchived(tag, !tag.archived)}
          />
          {#if !tag.reserved && tag.usage_count === 0}
            <Button
              size="sm"
              variant="tertiary"
              icon="delete-bin-line"
              iconOnly
              text={m['admin.voteTags.delete']()}
              title={m['admin.voteTags.delete']()}
              disabled={busy}
              onclick={() => remove(tag)}
            />
          {/if}
        </li>
      {/each}
    </ul>
  </section>
{/each}

<section class="mt-10">
  <h2 class="fr-h5">
    {editing ? m['admin.voteTags.editTitle']() : m['admin.voteTags.addTitle']()}
  </h2>

  <form class="max-w-2xl" onsubmit={editing ? saveEdit : create}>
    {#if !editing}
      <Select
        id="vote-tag-sign"
        bind:selected={newSign}
        label={m['admin.voteTags.signLabel']()}
        options={signs.map((value) => ({ value, label: m[`admin.voteTags.${value}`]() }))}
      />
    {/if}

    <Input
      id="vote-tag-emoji"
      value={editing ? editing.emoji : newEmoji}
      oninput={(event) => {
        const next = event.currentTarget.value
        if (editing) editing.emoji = next
        else newEmoji = next
      }}
      label={m['admin.voteTags.emojiLabel']()}
      maxlength={16}
    />

    {#each locales as locale (locale)}
      <Input
        id="vote-tag-label-{locale}"
        value={(editing ? editing.labels : newLabels)?.[locale] ?? ''}
        oninput={(event) => {
          const next = event.currentTarget.value
          if (editing) editing.labels = { ...(editing.labels ?? {}), [locale]: next }
          else newLabels = { ...newLabels, [locale]: next }
        }}
        label={m['admin.voteTags.labelFor']({ locale })}
        help={locale === baseLocale ? m['admin.voteTags.labelHelp']() : undefined}
        maxlength={100}
      />
    {/each}

    {#if editing}
      <p class="fr-text--sm text-grey">{m['admin.voteTags.keyFrozen']({ key: editing.key })}</p>
    {:else if keyPreview}
      <p class="fr-text--sm text-grey">{m['admin.voteTags.keyPreview']({ key: keyPreview })}</p>
    {/if}

    {#if formError}
      <p class="fr-error-text">{formError}</p>
    {/if}

    <div class="gap-2 mt-4 flex">
      <Button
        type="submit"
        disabled={busy}
        text={editing ? m['admin.voteTags.save']() : m['admin.voteTags.addTitle']()}
      />
      {#if editing}
        <Button
          type="button"
          variant="secondary"
          text={m['admin.voteTags.cancel']()}
          disabled={busy}
          onclick={() => {
            editing = undefined
            formError = undefined
          }}
        />
      {/if}
    </div>
  </form>
</section>
