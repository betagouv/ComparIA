<script
  lang="ts"
  generics="
    Col extends { id: string, label: string, orderable?: boolean, tooltip?: string }, 
    Row extends { id: string }
  "
>
  import { Button, Pagination, Select, Tooltip } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'
  import type { Snippet } from 'svelte'
  import type { HTMLTableAttributes } from 'svelte/elements'

  type TableProps = {
    caption: string
    cols: Col[]
    rows: Row[]
    pagination?: boolean
    orderingCol?: Col['id']
    orderingMethod?: 'ascending' | 'descending'
    hideCaption?: boolean
    cell: Snippet<[Row, Col]>
    header?: Snippet
  } & HTMLTableAttributes

  let {
    caption,
    cols,
    rows,
    pagination = false,
    orderingCol = $bindable(),
    orderingMethod = $bindable(),
    hideCaption = false,
    cell,
    header,
    class: classes,
    ...props
  }: TableProps = $props()

  function onOrderingColClick(col: Col) {
    if (orderingCol === col.id) {
      if (!orderingMethod) orderingMethod = 'descending'
      else if (orderingMethod === 'descending') orderingMethod = 'ascending'
      else orderingCol = undefined
    } else {
      orderingCol = col.id
      orderingMethod = 'descending'
    }
    // Also return to page 1
    page = 0
  }

  let page = $state(0)
  let maxRows = $state(10)

  const displayedRows = $derived(
    pagination ? rows.slice(page * maxRows, page * maxRows + maxRows) : rows
  )
  const maxRowsOptions = [10, 25, 50].map((value) => ({
    value,
    label: m['components.table.pageCount']({ count: value })
  }))
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
                        text={m['components.table.triage']()}
                        icon={col.id === orderingCol && orderingMethod === 'ascending'
                          ? 'sort-asc'
                          : 'sort-desc'}
                        size="xs"
                        variant="tertiary-no-outline"
                        iconOnly
                        aria-sort={col.id === orderingCol ? orderingMethod : undefined}
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

  {#if pagination}
    <div class="fr-table__footer">
      <div class="fr-table__footer--start">
        <Select
          bind:selected={maxRows}
          id="max-row-select"
          options={maxRowsOptions}
          label={m['components.table.linePerPage']()}
          hideLabel
        />
      </div>

      <div class="fr-table__footer--middle">
        <Pagination itemCount={rows.length} bind:page maxItemPerPage={maxRows} />
      </div>
    </div>
  {/if}
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
