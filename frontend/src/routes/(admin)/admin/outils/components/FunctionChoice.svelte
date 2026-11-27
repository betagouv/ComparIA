<script lang="ts">
  import { Checkbox } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'

  let {
    id,
    functions,
    value = $bindable()
  }: {
    id: string
    functions: { name: string; description?: string }[]
    value: string[] | null
  } = $props()

  // Servers write their descriptions for models, at length. The first
  // sentence is enough to choose by.
  function firstSentence(text = '') {
    return text.split(/(?<=\.)\s/)[0]
  }

  // No list means every function, those the server adds later included.
  // Ticking one narrows to a list; unticking the last goes back to all.
  function toggle(name: string, checked: boolean) {
    const others = (value ?? []).filter((n) => n !== name)
    const next = checked ? [...others, name] : others
    value = next.length ? next : null
  }
</script>

<div class="fr-fieldset__element">
  <Checkbox
    id="{id}-all"
    label={m['admin.tools.allFunctions']()}
    help={m['admin.tools.allFunctionsHint']()}
    disabled={value === null}
    bind:checked={
      () => value === null,
      (checked) => {
        if (checked) value = null
      }
    }
  />
</div>
{#each functions as fn (fn.name)}
  <div class="fr-fieldset__element">
    <Checkbox
      id="{id}-{fn.name}"
      label={fn.name}
      help={firstSentence(fn.description)}
      bind:checked={() => value?.includes(fn.name) ?? false, (checked) => toggle(fn.name, checked)}
    />
  </div>
{/each}
