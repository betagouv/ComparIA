<script module lang="ts">
  import type { PromptCheckCriterion as Criterion } from '$lib/generated/admin'

  // Four tints far apart: yellow replaces the DSFR orange, too close to red to
  // tell apart from a refusal, colour blind or not. Each tint also carries an
  // icon and a word, never the colour alone.
  export const actionTone: Record<Criterion['action'], { color: string; icon: string }> = {
    off: { color: 'var(--grey-425-625)', icon: 'i-ri-eye-off-line' },
    log: { color: 'var(--info-425-625)', icon: 'i-ri-eye-line' },
    warn: { color: 'var(--yellow-tournesol-main-731)', icon: 'i-ri-alert-line' },
    block: { color: 'var(--error-425-625)', icon: 'i-ri-forbid-line' }
  }
</script>

<script lang="ts">
  import { Button, Icon, Textarea } from '$components/dsfr'
  import { FormField, FormInput, FormSelect, type FormInputProps } from '$components/form'
  import type { PromptCheckCriterion } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import type { AnyFormItemProps } from '$lib/utils/form'
  import { actionLabels, actionOrder, keyFrom } from './criteria'

  let {
    criterion = $bindable(),
    id,
    fields,
    saved,
    takenKeys,
    errors,
    onremove
  }: {
    criterion: PromptCheckCriterion
    id: string
    fields: Record<string, AnyFormItemProps>
    // A saved criterion keeps its key: stored verdicts and the stats count by it.
    saved: boolean
    takenKeys: string[]
    errors: Record<string, string>
    onremove: () => void
  } = $props()

  const messageOptions = [
    { value: 'generic', label: m['admin.promptChecks.criteria.messages.generic']() },
    { value: 'self_harm', label: m['admin.promptChecks.criteria.messages.self_harm']() },
    { value: 'pii', label: m['admin.promptChecks.criteria.messages.pii']() }
  ]

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
        <Icon
          icon={actionTone[criterion.action].icon}
          size="xs"
          style="color: {actionTone[criterion.action].color}"
          aria-hidden="true"
        />
        {actionLabels[criterion.action]}
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

      <fieldset class="action-pills fr-fieldset mb-6!">
        <legend class="fr-label w-full">
          {fields.action.label}<span class="fr-sr-only"> : {name}</span>
        </legend>
        {#each actionOrder as option (option)}
          <input
            id="{id}-action-{option}"
            class="sr-only"
            type="radio"
            name="{id}-action"
            value={option}
            bind:group={criterion.action}
          />
          <label
            for="{id}-action-{option}"
            style="--pill-color: {actionTone[option]
              .color}; --pill-soft: color-mix(in srgb, {actionTone[option].color} 12%, transparent)"
          >
            <Icon icon={actionTone[option].icon} size="xs" class="pill-icon" aria-hidden="true" />
            {actionLabels[option]}
          </label>
        {/each}
      </fieldset>

      <div class="gap-x-4 md:grid-cols-2 grid">
        <FormInput
          {...input('threshold', { type: 'number', step: '0.05' })}
          bind:value={criterion.threshold}
        />
        <FormSelect
          {...fields.message}
          id="{id}-message"
          component="select"
          options={messageOptions}
          {errors}
          bind:value={criterion.message as string}
        />
      </div>

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

  .action-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
    margin: 0;
    padding: 0;
    border: 0;
  }

  .action-pills label {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.25rem 0.625rem;
    border: 1px solid var(--border-default-grey);
    border-radius: 999px;
    background: var(--background-default-grey);
    color: var(--text-mention-grey);
    font-size: 0.8125rem;
    line-height: 1.5;
    white-space: nowrap;
    cursor: pointer;
  }

  .action-pills label:hover {
    background: var(--background-default-grey-hover);
    color: var(--text-default-grey);
  }

  .action-pills input:checked + label {
    border-color: var(--pill-color);
    box-shadow: inset 0 0 0 1px var(--pill-color);
    background: var(--pill-soft);
    color: var(--text-default-grey);
    font-weight: 700;
  }

  .action-pills input:checked + label :global(.pill-icon),
  .action-pills label:hover :global(.pill-icon) {
    color: var(--pill-color);
  }

  .action-pills input:focus-visible + label {
    outline: 2px solid var(--outline-color);
    outline-offset: 2px;
  }
</style>
