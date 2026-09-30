<!--
  Test-only wrapper. Table needs a `cell` snippet, which a test cannot pass
  through @testing-library's plain props object.
-->
<script lang="ts">
  import type { TableCol } from '$lib/utils/data'
  import type { ComponentProps } from 'svelte'
  import Table from './Table.svelte'

  type Row = { id: string } & Record<string, unknown>

  let { rows, cols, ...props }: Omit<ComponentProps<typeof Table<TableCol, Row>>, 'cell'> = $props()
</script>

<Table {...props} {cols} {rows}>
  {#snippet cell(row, col)}
    {row[col.id]}
  {/snippet}
</Table>
