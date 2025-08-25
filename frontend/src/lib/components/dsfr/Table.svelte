<script
  lang="ts"
  generics="
    Col extends { id: string, label: string, orderable?: boolean, tooltip?: string }, 
    Row extends { id: string }
  "
>
  import Tooltip from '$components/Tooltip.svelte'
  import { sanitize } from '$lib/utils/commons'
  import type { Snippet } from 'svelte'
  import type { HTMLTableAttributes } from 'svelte/elements'
  import { Pagination, Select } from '.'
  import Button from './Button.svelte'

  type TableProps = {
    caption: string
    cols: Col[]
    rows: Row[]
    orderingCol?: Col['id']
    hideCaption?: boolean
    cell: Snippet<[Row, Col]>
    header?: Snippet
  } & HTMLTableAttributes

  let {
    caption,
    cols,
    rows,
    orderingCol = $bindable(),
    hideCaption = false,
    cell,
    header,
    class: classes,
    ...props
  }: TableProps = $props()

  function onOrderingColClick(col: Col) {
    if (orderingCol === col.id) orderingCol = undefined
    else orderingCol = col.id
    // Also return to page 1
    page = 0
  }

  let page = $state(0)
  let maxRows = $state(10)

  const displayedRows = $derived(rows.slice(page * maxRows, page * maxRows + maxRows))
  const maxRowsOptions = [10, 25, 50].map((value) => ({ value, label: `${value} lignes par page` }))
</script>

<div class={['fr-table', { 'fr-table--no-caption': hideCaption }, classes]}>
  {#if header}
    <div class="fr-table__header mb-4 flex flex-col gap-5 md:flex-row">
      {@render header()}
    </div>
  {/if}

  <div class="fr-table__wrapper">
    <div class="fr-table__container">
      <div class="fr-table__content">
        <table {...props}>
          <caption>{caption}</caption>

          <thead>
            <tr>
              {#each cols as col (col.id)}
                <th>
                  <div class="text-dark-grey! flex items-center text-xs font-medium">
                    <span>{@html sanitize(col.label)}</span>
                    {#if col.tooltip}
                      <Tooltip id={col.id} text={col.tooltip} size="xs" class="ms-1" />
                    {/if}
                    {#if col.orderable}
                      <Button
                        text="Trier"
                        icon="arrow-up-down-line"
                        size="xs"
                        variant="tertiary-no-outline"
                        iconOnly
                        class={['ms-1!', { 'text-dark-grey!': orderingCol !== col.id }]}
                        onclick={() => onOrderingColClick(col)}
                      />
                    {/if}
                  </div>
                </th>
              {/each}
            </tr>
          </thead>

          <tbody>
            {#each displayedRows as row, i (row.id)}
              <tr id={row.id} data-row-key={i}>
                {#each cols as col (`${col.id}-${row.id}`)}
                  <td>{@render cell(row, col)}</td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="fr-table__footer">
    <div class="fr-table__footer--start">
      <Select
        bind:selected={maxRows}
        id="max-row-select"
        options={maxRowsOptions}
        label="Nombre de lignes par page"
        hideLabel
      />
    </div>

    <div class="fr-table__footer--middle">
      <Pagination itemCount={rows.length} bind:page maxItemPerPage={maxRows} />
    </div>
  </div>
</div>

<style>
  .fr-table__wrapper::after {
    background-size:
      100% 1px,
      0px 100%,
      0px 100%,
      100% 1px !important;
  }

  .fr-table {
    --border-contrast-grey: #cacaca;
  }

  .fr-table__footer {
    border-top: 2px solid #8c8c8c;
  }

  thead tr {
    --border-plain-grey: none;
  }
</style>
