<script lang="ts" generics="T extends CriterionFields">
  import { Button, Icon, Textarea } from '$components/dsfr'
  import { FormField, FormInput, type FormInputProps } from '$components/form'
  import { m } from '$lib/i18n/messages'
  import type { AnyFormItemProps } from '$lib/utils/form'
  import type { Snippet } from 'svelte'
  import { keyFrom, type CriterionFields } from './criteria'

  let {
    criterion = $bindable(),
    id,
    fields,
    saved,
    takenKeys,
    errors,
    onremove,
    tag,
    settings
  }: {
    criterion: T
    id: string
    fields: Record<string, AnyFormItemProps>
    // A saved criterion keeps its key: stored verdicts and the stats count by it.
    saved: boolean
    takenKeys: string[]
    errors: Record<string, string>
    onremove: () => void
    // What each check adds: shown next to the name on the folded row, and
    // the fields under yes and no.
    tag: Snippet
    settings: Snippet
  } = $props()

  const name = $derived(criterion.label || criterion.key)
  const hasError = $derived(Object.keys(errors).some((key) => key.startsWith(`${id}-`)))

  function input(field: string, props: Partial<FormInputProps> = {}) {
    return { ...fields[field], id: `${id}-${field}`, errors, ...props } as FormInputProps
  }

  // A new criterion takes its key from its name, as long as it is unsaved.
  function setLabel(label: string) {
    criterion.label = label
    if (!saved) criterion.key = keyFrom(label, takenKeys)
  }
</script>

<li {id} class="border-0 border-b border-solid border-[--border-default-grey] last:border-b-0">
  <!-- Folded once saved: nine open criteria make an endless page. An error
       opens its own, or it would stay hidden. -->
  <details class="criterion" open={!saved || hasError}>
    <summary class="gap-3 py-3 px-1 flex cursor-pointer items-center">
      <Icon icon="i-ri-arrow-right-s-line" size="sm" class="chevron shrink-0" aria-hidden="true" />
      <span class="text-dark-grey min-w-0 font-medium flex-1 truncate">
        {name || m['admin.promptChecks.criteria.new']()}
      </span>
      <span class="gap-1 text-xs text-grey flex shrink-0 items-center">
        {@render tag()}
      </span>
      <span class="text-xs text-grey w-[5.5rem] shrink-0 text-right tabular-nums">
        {fields.threshold.label}
        {String(criterion.threshold).replace('.', ',')}
      </span>
    </summary>

    <div class="px-1 pb-4">
      <FormInput {...input('label')} bind:value={() => criterion.label, setLabel} />
      <FormInput
        {...input('key', { disabled: saved, required: !saved })}
        bind:value={criterion.key}
      />
      <!-- A question runs to a sentence or two: one line would cut it off. -->
      <FormField {...fields.question} id="{id}-question" {errors} component="input">
        {#snippet formItem(fieldProps)}
          <textarea {...fieldProps} class="fr-input mt-2" rows={2} bind:value={criterion.question}
          ></textarea>
        {/snippet}
      </FormField>

      <div class="gap-x-4 md:grid-cols-2 mb-6 grid">
        {#each ['yes', 'no'] as const as field (field)}
          <Textarea
            id="{id}-{field}"
            label={fields[field].label}
            error={errors[`${id}-${field}`]}
            rows={5}
            bind:value={criterion[field]!}
          />
        {/each}
      </div>

      {@render settings()}

      <Button
        id="{id}-remove"
        variant="tertiary"
        size="sm"
        icon="delete-line"
        text={m['admin.promptChecks.criteria.remove']()}
        aria-label="{m['admin.promptChecks.criteria.remove']()} : {name}"
        onclick={onremove}
      />
    </div>
  </details>
</li>

<style lang="postcss">
  .criterion summary {
    list-style: none;
  }

  .criterion summary::-webkit-details-marker {
    display: none;
  }

  /* The DSFR fields are content-box: at full width, their padding pushed the
     text boxes and the select past the edge of their column. */
  .criterion :global(.fr-input),
  .criterion :global(.fr-select) {
    box-sizing: border-box;
  }

  /* Grows with its text where the browser can, so none of it hides behind a
     scrollbar; elsewhere it keeps its rows and can be dragged taller. */
  .criterion :global(textarea.fr-input) {
    field-sizing: content;
    min-height: 3lh;
    resize: vertical;
  }

  .criterion summary:hover {
    background: var(--background-default-grey-hover);
  }

  .criterion summary:focus-visible {
    outline: 2px solid var(--outline-color);
    outline-offset: 2px;
  }

  .criterion :global(.chevron) {
    transition: transform 0.15s;
  }

  .criterion[open] :global(.chevron) {
    transform: rotate(90deg);
  }
</style>
