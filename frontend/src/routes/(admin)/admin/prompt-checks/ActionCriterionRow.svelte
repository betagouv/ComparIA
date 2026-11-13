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
  import CriterionRow from '$components/admin/CriterionRow.svelte'
  import { Icon } from '$components/dsfr'
  import { FormInput, FormSelect, type FormInputProps } from '$components/form'
  import { m } from '$lib/i18n/messages'
  import type { AnyFormItemProps } from '$lib/utils/form'
  import { actionLabels, actionOrder } from './criteria'

  let {
    criterion = $bindable(),
    id,
    fields,
    errors,
    ...row
  }: {
    criterion: Criterion
    id: string
    fields: Record<string, AnyFormItemProps>
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
</script>

<CriterionRow {id} {fields} {errors} {...row} bind:criterion>
  {#snippet tag()}
    <Icon
      icon={actionTone[criterion.action].icon}
      size="xs"
      style="color: {actionTone[criterion.action].color}"
      aria-hidden="true"
    />
    {actionLabels[criterion.action]}
  {/snippet}
  {#snippet settings()}
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
        {...fields.threshold as FormInputProps}
        id="{id}-threshold"
        type="number"
        step="0.05"
        {errors}
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
  {/snippet}
</CriterionRow>

<style lang="postcss">
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
