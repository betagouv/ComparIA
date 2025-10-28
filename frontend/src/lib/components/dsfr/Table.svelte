<script
  lang="ts"
  generics="
    Col extends { id: string, label: string, orderable?: boolean, tooltip?: string, colHeaderClass?: ClassValue }, 
    Row extends { id: string }
  "
>
  import { Button, Pagination, Search, Select, Tooltip } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'
  import { onMount, type Snippet } from 'svelte'
  import type { ClassValue, HTMLTableAttributes } from 'svelte/elements'

  type TableProps = {
    caption: string
    cols: Col[]
    rows: Row[]
    pagination?: boolean
    orderingCol?: Col['id']
    orderingMethod?: 'ascending' | 'descending'
    search?: string
    searchLabel?: string
    hideCaption?: boolean
    cell: Snippet<[Row, Col]>
    headerLeft?: Snippet
    headerRight?: Snippet
  } & HTMLTableAttributes

  let {
    id,
    caption,
    cols,
    rows,
    pagination = false,
    orderingCol = $bindable(),
    orderingMethod = $bindable(),
    search = $bindable(),
    searchLabel = m['words.search'](),
    hideCaption = false,
    cell,
    headerLeft,
    headerRight,
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

  let containerElem = $state<HTMLDivElement>()
  let scrollable = $state({ left: false, right: false })
  let stickyElem = $state<HTMLDivElement>()

  function updateGradientDisplay() {
    scrollable.left = containerElem!.scrollLeft !== 0
    scrollable.right =
      containerElem!.offsetWidth + containerElem!.scrollLeft < containerElem!.scrollWidth
  }

  function scrollTable(direction: -1 | 1) {
    const { offsetWidth, scrollLeft } = containerElem!
    const cols = Array.from(containerElem!.querySelectorAll<HTMLHtmlElement>('thead th')).reverse()
    const col = cols.find((col) => {
      const offsetLeft = col.offsetLeft - direction
      return direction === 1 ? offsetLeft <= offsetWidth + scrollLeft : offsetLeft <= scrollLeft
    })

    if (!col) return

    containerElem!.scrollTo({
      left: direction === 1 ? col.offsetLeft + col.offsetWidth - offsetWidth : col.offsetLeft
    })
  }

  function onscroll() {
    // Can't use 'sticky' here, multiple parents have 'overflow', so use js
    const parent = stickyElem!.parentElement!
    const { top } = parent.getBoundingClientRect()
    const pos = top >= 0 ? 0 : Math.abs(top)
    stickyElem!.style = `top: ${pos}px;`
  }

  onMount(() => {
    updateGradientDisplay()
    onscroll()
  })
</script>

<svelte:window onresize={() => updateGradientDisplay()} {onscroll} />

<div class={['fr-table', { 'fr-table--no-caption': hideCaption }, classes]}>
  <div class="fr-table__header mb-4 flex flex-col gap-5 md:flex-row md:flex-wrap">
    <div class="flex flex-wrap items-center gap-5">
      {@render headerLeft?.()}
    </div>

    <div class="flex flex-col gap-5 md:flex-row md:items-center">
      {@render headerRight?.()}

      {#if search !== undefined}
        <Search
          id="table-search"
          bind:value={search}
          label={searchLabel}
          class="ms-auto w-full md:w-auto"
        />
      {/if}

      {#if scrollable.left || scrollable.right}
        <div class="flex w-full justify-between gap-2 md:w-auto">
          <Button
            text={m['actions.scrollLeft']()}
            icon="arrow-left-line"
            iconOnly
            variant="tertiary"
            disabled={!scrollable.left}
            onclick={() => scrollTable(-1)}
          />
          <Button
            text={m['actions.scrollRight']()}
            icon="arrow-right-line"
            iconOnly
            variant="tertiary"
            disabled={!scrollable.right}
            class="ms-auto md:ms-0"
            onclick={() => scrollTable(1)}
          />
        </div>
      {/if}
    </div>
  </div>

  <div class="fr-table__wrapper relative">
    <div
      id="table-gradient"
      class={['z-3 absolute inset-0 start-[80%] md:start-[95%]', { hidden: !scrollable.right }]}
    ></div>

    <div
      bind:this={containerElem}
      class="fr-table__container overflow-y-hidden!"
      onscroll={() => updateGradientDisplay()}
    >
      <div class="fr-table__content">
        <table {id} {...props}>
          <caption>{caption}</caption>

          <thead bind:this={stickyElem} class="z-2 relative">
            <tr>
              {#each cols as col (col.id)}
                <th class={col.colHeaderClass}>
                  <div class="text-dark-grey! flex items-center text-xs font-medium">
                    <span>{@html sanitize(col.label)}</span>
                    {#if col.tooltip}
                      <Tooltip id="{id}-{col.id}" text={col.tooltip} size="xs" class="ms-1" />
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

  #table-gradient {
    background: linear-gradient(
      90deg,
      rgba(255, 255, 255, 0) 0%,
      rgba(135, 135, 135, 0.15) 50%,
      rgba(135, 135, 135, 0.2) 100%
    );
  }
</style>
