<!--
  Test-only wrapper. Table needs a `cell` snippet, which a test cannot pass
  through @testing-library's plain props object.
-->
<script lang="ts">
  import Table from './Table.svelte'

  let { rows, cols, ...props }: Record<string, unknown> = $props()
</script>

<Table {...props} {cols} {rows}>
  {#snippet cell(row, col)}
    {row[col.id]}
  {/snippet}
</Table>
