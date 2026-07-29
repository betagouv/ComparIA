<script lang="ts">
  import { Icon } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { SOVEREIGNTY_FIELDS, type BotModel } from '$lib/models'

  let {
    model,
    detailed = false
  }: {
    model: BotModel
    detailed?: boolean
  } = $props()

  let expanded = $state(false)

  const criteria = $derived(
    SOVEREIGNTY_FIELDS.map((id) => {
      const value = id === 'commercial_use' || id === 'reuse' ? model.license[id] : model[id]
      return {
        id,
        label: m[`models.opennessSovereignty.fields.${id}`](),
        value
      }
    })
  )

  const score = $derived(`${model.sovereignty_score}/${SOVEREIGNTY_FIELDS.length}`)
</script>

{#if detailed}
  <div class="group relative inline-flex">
    <button
      type="button"
      class="relative z-10 flex min-h-8 min-w-10 items-center justify-center rounded-sm border-0 bg-transparent px-1 py-0.5 transition-transform hover:bg-[--grey-1000] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary active:scale-95"
      aria-controls="openness-score-{model.id}"
      aria-expanded={expanded}
      onclick={(event) => {
        event.preventDefault()
        event.stopPropagation()
        expanded = !expanded
      }}
    >
      <strong class="text-base leading-none" aria-hidden="true">{score}</strong>
      <span class="sr-only">{m['models.opennessSovereignty.title']()} : {score}</span>
    </button>

    <div
      id="openness-score-{model.id}"
      class={[
        'pointer-events-none absolute z-50 bottom-full left-1/2 mb-2 w-[calc(100vw-2rem)] max-w-72 -translate-x-1/2 rounded-lg bg-white p-4 shadow-lg transition-opacity group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100',
        expanded ? 'visible opacity-100' : 'invisible opacity-0'
      ]}
      role="tooltip"
    >
      <p class="text-primary mb-3! text-xs font-bold uppercase tracking-[0.08em]">
        {m['models.opennessSovereignty.title']()}
      </p>
      <div class="mb-4 gap-1.5 flex items-center">
        <div class="gap-1 flex" aria-hidden="true">
          {#each criteria as criterion (criterion.id)}
            <span
              class={[
                'rounded-xs h-3 w-7',
                criterion.value ? 'bg-success' : 'bg-[--grey-900-175]'
              ]}
            ></span>
          {/each}
        </div>
        <strong class="text-lg leading-none">{score}</strong>
      </div>
      <ul class="gap-x-4 gap-y-1 m-0! grid list-none grid-cols-2 p-0">
        {#each criteria as criterion (criterion.id)}
          <li class="gap-1 m-0! flex items-center text-xs leading-tight">
            <Icon
              icon={criterion.value ? 'i-ri-check-line' : 'i-ri-close-line'}
              size="xs"
              class={criterion.value ? 'text-success' : 'text-error'}
            />
            <span>{criterion.label}</span>
          </li>
        {/each}
      </ul>
    </div>
  </div>
{:else}
  <strong class="text-lg leading-none">{score}</strong>
{/if}
