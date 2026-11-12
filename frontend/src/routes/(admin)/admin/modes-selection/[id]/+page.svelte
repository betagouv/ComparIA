<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { resolve } from '$app/paths'
  import Link from '$components/dsfr/Link.svelte'
  import { getLocalesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { ModeEditor } from '../components'
  import { buildCatalogue, buildLookups } from '../filter'
  import { modeLabel, toForm } from '../mode'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()
  const locales = getLocalesContext()

  const catalogue = $derived(buildCatalogue(data))
  const lookups = $derived(buildLookups(data))
  const label = $derived(modeLabel(data.mode, locales))
</script>

{#key data.mode.id}
  <ModeEditor
    initial={toForm(data.mode)}
    modeId={data.mode.id}
    schema={data.schema}
    takenKeys={data.modes.map((mode) => mode.key)}
    {catalogue}
    {lookups}
    tools={data.tools}
    cohorts={data.cohorts}
    onsaved={() => invalidate('admin:selection-modes')}
  >
    {#snippet header()}
      <Link
        href={resolve('/admin/modes-selection')}
        text={m['admin.selectionModes.editor.back']()}
        icon="arrow-left-line"
        size="sm"
        class="mb-4"
      />
      <h2 class="fr-h3 mb-6!">{m['admin.selectionModes.editor.editTitle']({ label })}</h2>
    {/snippet}
  </ModeEditor>
{/key}
