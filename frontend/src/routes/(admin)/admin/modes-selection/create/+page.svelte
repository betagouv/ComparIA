<script lang="ts">
  import { goto, invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Button, Icon } from '$components/dsfr'
  import Link from '$components/dsfr/Link.svelte'
  import type { SelectionModeTemplate } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import { tick } from 'svelte'
  import { ModeEditor } from '../components'
  import { buildCatalogue, buildLookups } from '../filter'
  import { toForm, uniqueModeKey, type ModeForm } from '../mode'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()

  const catalogue = $derived(buildCatalogue(data))
  const lookups = $derived(buildLookups(data))
  const takenKeys = $derived(data.modes.map((mode) => mode.key))

  let initial = $state.raw<ModeForm>()
  let startedFrom = $state<string>()
  let heading = $state<HTMLHeadingElement>()

  // A template's texts are messages under its id; one the frontend does not
  // know yet shows its id.
  const messages = m as unknown as Record<string, (() => string) | undefined>
  const templateText = (template: SelectionModeTemplate, part: 'title' | 'description') =>
    messages[`admin.selectionModes.templates.${template.id}.${part}`]?.() ?? template.id

  async function start(template?: SelectionModeTemplate) {
    const form = toForm(template?.mode ?? { label: {} })
    // A template names its key; a second mode from it gets a number.
    if (form.key) form.key = uniqueModeKey(form.key, takenKeys)
    initial = form
    startedFrom = template ? templateText(template, 'title') : undefined
    await tick()
    heading?.focus()
  }

  async function backToGallery(dirty: boolean) {
    if (dirty && !window.confirm(m['form.unsavedChanges']())) return
    initial = undefined
    await tick()
    heading?.focus()
  }
</script>

{#if !initial}
  <Link
    href={resolve('/admin/modes-selection')}
    text={m['admin.selectionModes.editor.back']()}
    icon="arrow-left-line"
    size="sm"
    class="mb-4"
  />
  <h2 bind:this={heading} tabindex="-1" class="fr-h3 mb-2! outline-none">
    {m['admin.selectionModes.gallery.title']()}
  </h2>
  <p class="mb-6! max-w-[700px] text-[--text-mention-grey]">
    {m['admin.selectionModes.gallery.intro']()}
  </p>

  <ul class="gap-4 m-0! p-0! sm:grid-cols-2 xl:grid-cols-3 grid list-none">
    <li class="p-0!">
      <button type="button" class="template-card blank" onclick={() => start()}>
        <Icon
          icon="i-ri-file-add-line"
          class="mb-3 text-2xl text-[--text-action-high-blue-france]"
          aria-hidden="true"
        />
        <span class="fr-text--lg font-bold mb-1! block"
          >{m['admin.selectionModes.gallery.blank']()}</span
        >
        <span class="fr-text--sm mb-0! block text-[--text-mention-grey]">
          {m['admin.selectionModes.gallery.blankHelp']()}
        </span>
      </button>
    </li>
    {#each data.templates as template (template.id)}
      <li class="p-0!">
        <button type="button" class="template-card" onclick={() => start(template)}>
          <Icon
            icon={template.mode.icon || 'i-ri-dice-line'}
            class="mb-3 text-2xl text-[--text-action-high-blue-france]"
            aria-hidden="true"
          />
          <span class="fr-text--lg font-bold mb-1! block">{templateText(template, 'title')}</span>
          <span class="fr-text--sm mb-0! block text-[--text-mention-grey]">
            {templateText(template, 'description')}
          </span>
        </button>
      </li>
    {/each}
  </ul>
{:else}
  <ModeEditor
    {initial}
    schema={data.schema}
    {takenKeys}
    {catalogue}
    {lookups}
    tools={data.tools}
    cohorts={data.cohorts}
    onsaved={async (saved) => {
      await invalidate('admin:selection-modes')
      await goto(resolve(`/admin/modes-selection/${saved.id}`))
    }}
  >
    {#snippet header(dirty)}
      <Button
        size="sm"
        variant="tertiary-no-outline"
        icon="arrow-left-line"
        text={m['admin.selectionModes.gallery.change']()}
        class="mb-4"
        onclick={() => backToGallery(dirty)}
      />
      <h2 bind:this={heading} tabindex="-1" class="fr-h3 mb-1! outline-none">
        {m['admin.selectionModes.editor.createTitle']()}
      </h2>
      <p class="fr-text--sm mb-6! text-[--text-mention-grey]">
        {startedFrom
          ? m['admin.selectionModes.gallery.startedFrom']({ template: startedFrom })
          : m['admin.selectionModes.gallery.startedBlank']()}
      </p>
    {/snippet}
  </ModeEditor>
{/if}

<style>
  .template-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    width: 100%;
    height: 100%;
    padding: 1.25rem;
    text-align: left;
    border: 1px solid var(--border-default-grey);
    border-radius: 0.75rem;
    background-color: var(--background-default-grey);
    transition:
      border-color 0.15s,
      background-color 0.15s;
  }

  .template-card:hover {
    border-color: var(--border-action-high-blue-france);
    background-color: var(--background-default-grey-hover);
  }

  .template-card.blank {
    border-style: dashed;
  }

  @media (prefers-reduced-motion: reduce) {
    .template-card {
      transition: none;
    }
  }
</style>
