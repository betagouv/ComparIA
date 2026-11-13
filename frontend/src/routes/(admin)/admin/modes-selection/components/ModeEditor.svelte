<script lang="ts">
  import IconPicker from '$components/admin/IconPicker.svelte'
  import { Button, Checkbox, Toggle } from '$components/dsfr'
  import {
    FormInput,
    FormToggle,
    type FormInputProps,
    type FormToggleProps
  } from '$components/form'
  import Form from '$components/form/Form.svelte'
  import FormTranslate from '$components/form/FormTranslate.svelte'
  import type { SelectionModeAdmin, SelectionModePreview, ToolAdmin } from '$lib/generated/admin'
  import { MODE_ICONS, type ModeIcons } from '$lib/generated/constants'
  import { getLocalesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import type { Locale } from '$lib/i18n/runtime'
  import { useFormSchema } from '$lib/stores/form.svelte'
  import type { AnyFormItemProps, FormSection, JSONSchema } from '$lib/utils/form'
  import { untrack, type Snippet } from 'svelte'
  import { MODE_ERROR_FIELDS, MODE_ERRORS } from '../errors'
  import type { Catalogue } from '../filter'
  import { ROW_FIELDS, toModeKey, toRules, toUpsert, uniqueModeKey, type ModeForm } from '../mode'
  import { shortList, type Lookups } from '../summary'
  import ModelFilterBuilder from './ModelFilterBuilder.svelte'
  import PreviewPanel from './PreviewPanel.svelte'

  let {
    initial,
    modeId,
    schema,
    takenKeys,
    catalogue,
    lookups,
    tools,
    cohorts,
    onsaved,
    header
  }: {
    initial: ModeForm
    /** Set when editing a saved mode. */
    modeId?: string
    schema: JSONSchema
    takenKeys: string[]
    catalogue: Catalogue
    lookups: Lookups
    tools: ToolAdmin[]
    cohorts: string[]
    onsaved: (mode: SelectionModeAdmin) => void | Promise<void>
    /** Told whether the form holds changes not saved yet. */
    header?: Snippet<[dirty: boolean]>
  } = $props()

  const locales = getLocalesContext()

  const form = $derived(
    useFormSchema({
      url: modeId ? `/admin/selection-modes/${modeId}` : '/admin/selection-modes',
      method: modeId ? 'put' : 'post',
      initialData: () => initial,
      schema: () => schema,
      omitKeys: ROW_FIELDS,
      i18nKey: 'selection_mode_upsert',
      errorMessages: MODE_ERRORS,
      errorFields: MODE_ERROR_FIELDS,
      onBeforeSubmit: (values, errors) => {
        if (!values.label[locales.default]?.trim()) {
          errors.label = m['admin.selectionModes.errors.labelDefaultLocale']()
          return null
        }
        return toUpsert(values)
      },
      onSuccess: (saved) => onsaved(saved as unknown as SelectionModeAdmin)
    })
  )
  const values = $derived(form.form)

  // A new mode's key follows its label until the admin types one.
  let keyTouched = $state(untrack(() => !!modeId || !!initial.key))
  let preview = $state<SelectionModePreview>()

  const rules = $derived(toRules(values))
  const split = $derived(!!values.pool_b)

  // A locale saved on the mode stays visible after it was switched off for
  // the instance, so it can be unticked.
  const localeOptions = $derived(
    locales.asOptions([
      ...locales.enabled,
      ...values.locales.filter((locale) => !locales.enabled.includes(locale))
    ])
  )

  // The schema marks a field required when it cannot be null; only the ones
  // without a default must be filled in.
  const items = $derived(
    form.items.map((item) => ({
      ...item,
      required: !!schema.required?.includes(item.id),
      ...(item.id === 'cohorts' ? { suggestions: cohorts } : {}),
      ...(item.id === 'locales' ? { options: localeOptions } : {})
    })) as AnyFormItemProps[]
  )
  const field = (id: string) => items.find((item) => item.id === id)!

  const sections: FormSection[] = $derived([
    {
      id: 'identity',
      title: m['admin.selectionModes.identity.title'](),
      intro: m['admin.selectionModes.identity.intro'](),
      items: [['key'], 'icon', 'label']
    },
    {
      id: 'picks',
      title: m['admin.selectionModes.picks.title'](),
      intro: m['admin.selectionModes.picks.intro'](),
      items: ['visitor_picks']
    },
    {
      id: 'pool-a',
      title: split ? field('pool_a').label : m['admin.selectionModes.pool.title'](),
      intro: split
        ? m['admin.selectionModes.poolA.intro']()
        : m['admin.selectionModes.pool.intro'](),
      items: ['pool_a']
    },
    ...(split
      ? [
          {
            id: 'pool-b',
            title: field('pool_b').label,
            intro: m['admin.selectionModes.poolB.intro'](),
            items: ['pool_b']
          }
        ]
      : []),
    {
      id: 'draw',
      title: m['admin.selectionModes.draw.title'](),
      intro: m['admin.selectionModes.draw.intro'](),
      items: ['pairing', 'sampling']
    },
    {
      id: 'tools',
      title: m['admin.selectionModes.tools.title'](),
      intro: m['admin.selectionModes.tools.intro'](),
      items: ['tools_policy', 'tool_keys']
    },
    {
      id: 'audience',
      title: m['admin.selectionModes.audience.title'](),
      intro: m['admin.selectionModes.audience.intro'](),
      items: ['cohorts', 'locales', ['starts_at', 'ends_at']]
    },
    {
      id: 'publish',
      title: m['admin.selectionModes.publish.title'](),
      intro: m['admin.selectionModes.publish.intro'](),
      items: ['enabled', 'is_default']
    }
  ])

  // Every icon the backend accepts, with its name for screen readers. The
  // Record makes a new icon in the list fail the type check until it is named.
  const iconLabels: Record<ModeIcons, () => string> = {
    'i-ri-dice-line': m['admin.selectionModes.icons.dice'],
    'i-ri-scales-3-line': m['admin.selectionModes.icons.scales'],
    'i-ri-open-source-line': m['admin.selectionModes.icons.openSource'],
    'i-ri-map-pin-line': m['admin.selectionModes.icons.mapPin'],
    'i-ri-ruler-line': m['admin.selectionModes.icons.ruler'],
    'i-ri-leaf-line': m['admin.selectionModes.icons.leaf'],
    'i-ri-trophy-line': m['admin.selectionModes.icons.trophy'],
    'i-ri-sparkling-line': m['admin.selectionModes.icons.sparkling'],
    'i-ri-group-line': m['admin.selectionModes.icons.group'],
    'i-ri-search-line': m['admin.selectionModes.icons.search'],
    'i-ri-global-line': m['admin.selectionModes.icons.global'],
    'i-ri-government-line': m['admin.selectionModes.icons.government'],
    'i-ri-heart-pulse-line': m['admin.selectionModes.icons.health'],
    'i-ri-stethoscope-line': m['admin.selectionModes.icons.stethoscope'],
    'i-ri-graduation-cap-line': m['admin.selectionModes.icons.learning'],
    'i-ri-shield-check-line': m['admin.selectionModes.icons.shield'],
    'i-ri-flashlight-line': m['admin.selectionModes.icons.flash']
  }
  const icons = MODE_ICONS.map((icon) => ({ value: icon, label: iconLabels[icon]() }))

  // Models in the pools that bring their own tools: whatever the policy,
  // the arena never hands them its tools. Read from the preview, which is
  // fresher than the catalogue loaded with the page.
  const ownTools = $derived.by(() => {
    if (!preview) return []
    const own = [...preview.pool_a, ...preview.pool_b].filter((llm) => !llm.arena_tools)
    return [...new Set(own.map((llm) => llm.name))]
  })

  function toolLabel(key: string) {
    return tools.find((tool) => tool.key === key)?.label ?? key
  }

  // A saved tool that has since been removed still shows, to be unticked.
  const toolChoices = $derived([
    ...tools.map((tool) => ({ key: tool.key, label: tool.label, enabled: tool.enabled ?? false })),
    ...values.tool_keys
      .filter((key) => !tools.some((tool) => tool.key === key))
      .map((key) => ({ key, label: key, enabled: false }))
  ])

  function setLabel(locale: Locale, text: string) {
    values.label[locale] = text
    if (!keyTouched && locale === locales.default) {
      values.key = uniqueModeKey(toModeKey(text), takenKeys)
    }
  }

  function toggleTool(key: string, checked: boolean) {
    const others = values.tool_keys.filter((other) => other !== key)
    values.tool_keys = checked ? [...others, key] : others
  }
</script>

{#snippet key()}
  <FormInput
    {...field('key') as FormInputProps}
    help={modeId ? m['admin.selectionModes.identity.keyFrozen']() : field('key').help}
    disabled={!!modeId}
    maxlength={50}
    errors={form.errors}
    bind:value={
      () => values.key,
      (key) => {
        keyTouched = true
        values.key = String(key ?? '')
      }
    }
  />
{/snippet}

{#snippet icon()}
  <IconPicker
    id="icon"
    label={field('icon').label}
    options={icons}
    bind:value={() => values.icon, (icon) => (values.icon = icon as ModeIcons)}
  />
{/snippet}

{#snippet texts()}
  <FormTranslate id="mode-texts" bind:value={values.label}>
    {#snippet subSnippet(locale, localeLabel)}
      <FormInput
        id={locale === locales.default ? 'label' : `label-${locale}`}
        type="text"
        label="{field('label').label} ({localeLabel})"
        help={locale === locales.default
          ? field('label').help
          : m['admin.selectionModes.identity.labelOtherHelp']()}
        maxlength={60}
        required={locale === locales.default}
        errors={form.errors}
        bind:value={
          () => values.label[locale] ?? '', (text) => setLabel(locale, String(text ?? ''))
        }
      />
      <FormInput
        id="short_label-{locale}"
        type="text"
        label={field('short_label').label}
        help={field('short_label').help}
        maxlength={60}
        bind:value={
          () => values.short_label[locale] ?? '',
          (text) => (values.short_label[locale] = String(text ?? ''))
        }
      />
      <FormInput
        id="description-{locale}"
        type="text"
        label={field('description').label}
        help={field('description').help}
        maxlength={160}
        bind:value={
          () => values.description[locale] ?? '',
          (text) => (values.description[locale] = String(text ?? ''))
        }
      />
    {/snippet}
  </FormTranslate>
{/snippet}

{#snippet poolA()}
  <ModelFilterBuilder
    id="pool_a"
    bind:value={values.pool_a}
    {catalogue}
    {lookups}
    errors={form.errors}
  />
  <Toggle
    id="pool-b-switch"
    label={m['admin.selectionModes.poolB.switch']()}
    help={m['admin.selectionModes.poolB.switchHelp']()}
    labelPos="right"
    class="mt-6"
    bind:value={() => split, (on) => (values.pool_b = on ? {} : null)}
  />
{/snippet}

{#snippet poolB()}
  <ModelFilterBuilder
    id="pool_b"
    bind:value={() => values.pool_b ?? {}, (next) => (values.pool_b = next)}
    {catalogue}
    {lookups}
    errors={form.errors}
  />
{/snippet}

{#snippet toolKeys()}
  {#if values.tools_policy !== 'none' && ownTools.length}
    <p class="fr-text--sm mb-4! gap-2 flex text-[--text-mention-grey]">
      <span class="i-ri-information-line mt-0.5 shrink-0" aria-hidden="true"></span>
      {m['admin.selectionModes.tools.ownTools']({ names: shortList(ownTools) })}
    </p>
  {/if}
  {#if values.tools_policy !== 'none'}
    <fieldset
      id="tool_keys"
      class={['fr-fieldset mb-0!', { 'fr-fieldset--error': !!form.errors.tool_keys }]}
      aria-describedby="tool-keys-hint tool-keys-messages"
    >
      <legend class="fr-fieldset__legend">
        {field('tool_keys').label}
        <span id="tool-keys-hint" class="fr-hint-text">
          {values.tools_policy === 'forced'
            ? m['admin.selectionModes.tools.listForcedHelp']()
            : m['admin.selectionModes.tools.listVisitorHelp']()}
        </span>
      </legend>
      {#each toolChoices as tool (tool.key)}
        <div class="fr-fieldset__element">
          <Checkbox
            id="tool-{tool.key}"
            label={tool.label}
            help={tool.enabled
              ? tool.key
              : m['admin.selectionModes.tools.switchedOff']({ key: tool.key })}
            bind:checked={
              () => values.tool_keys.includes(tool.key), (checked) => toggleTool(tool.key, checked)
            }
          />
        </div>
      {:else}
        <p class="fr-text--sm text-[--text-mention-grey]">
          {m['admin.selectionModes.tools.noTools']()}
        </p>
      {/each}
      <div class="fr-messages-group" id="tool-keys-messages" aria-live="polite">
        {#if form.errors.tool_keys}
          <p class="fr-message fr-message--error">{form.errors.tool_keys}</p>
        {/if}
      </div>
    </fieldset>
  {/if}
{/snippet}

{#snippet isDefault()}
  <FormToggle
    {...field('is_default') as FormToggleProps}
    help={initial.is_default && modeId
      ? m['admin.selectionModes.publish.isDefaultHelp']()
      : field('is_default').help}
    disabled={!values.enabled}
    errors={form.errors}
    bind:value={values.is_default}
  />
{/snippet}

{#snippet saveBar(isBusy: boolean)}
  <p class="fr-text--sm mb-0! min-w-0 lg:hidden me-auto">
    {#if preview}
      <a
        href="#mode-preview-title"
        class={{ 'text-[--text-default-error]': !preview.viability.viable }}
      >
        {preview.viability.viable
          ? m['admin.selectionModes.editor.statusOk']({ pairs: preview.viability.pairs })
          : m['admin.selectionModes.editor.statusBad']()}
      </a>
    {/if}
  </p>
  <p class="fr-text--sm mb-0! lg:block me-auto hidden self-center text-[--text-mention-grey]">
    {form.isDirty ? m['admin.selectionModes.editor.unsaved']() : ''}
  </p>
  <Button
    type="submit"
    icon="check-line"
    text={isBusy ? m['form.busy']() : m['words.save']()}
    disabled={isBusy}
  />
{/snippet}

{@render header?.(form.isDirty)}

<div
  class="mode-editor gap-8 lg:grid-cols-[minmax(0,1fr)_22rem] xl:grid-cols-[minmax(0,1fr)_26rem] grid"
>
  <Form
    id="mode-editor"
    {...form}
    {items}
    {sections}
    stickyFooter
    fieldSnippets={{
      key,
      icon,
      label: texts,
      pool_a: poolA,
      pool_b: poolB,
      tool_keys: toolKeys,
      is_default: isDefault
    }}
    btnSnippet={saveBar}
    class="min-w-0"
  />

  <aside class="min-w-0" aria-label={m['admin.selectionModes.preview.title']()}>
    <div class="lg:top-6 lg:sticky">
      <PreviewPanel {rules} {toolLabel} bind:preview />
    </div>
  </aside>
</div>

<style>
  /* A fieldset grows to its widest content by default, which pushes a row
     of radio buttons off a phone screen instead of letting it scroll. */
  .mode-editor :global(fieldset) {
    min-width: 0;
  }
</style>
