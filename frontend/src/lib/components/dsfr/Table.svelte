<script lang="ts" generics="Col extends TableCol, Row extends { id: string }">
  import { Button, Pagination, Search, Select, Tooltip } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'
  import type { OrderingMethod, TableCol } from '$lib/utils/data'
  import { browser } from '$app/environment'
  import { onMount, type Snippet } from 'svelte'
  import { flip } from 'svelte/animate'
  import type { HTMLAttributes, HTMLTableAttributes } from 'svelte/elements'

  /** Column labels may carry markup; an accessible name has to be plain text. */
  const stripTags = (label: string) =>
    label
      .replace(/<[^>]*>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()

  type TableProps = {
    caption: string
    cols: Col[]
    rows: Row[]
    itemCount?: number
    maxRowsPerPage?: number
    currentPage?: number
    orderingCol?: Col['id']
    orderingMethod?: OrderingMethod
    search?: string
    searchLabel?: string
    hideCaption?: boolean
    cell: Snippet<[Row, Col]>
    headerLeft?: Snippet
    headerRight?: Snippet
    // Attributes to put on a row's <tr>, for tables where the row itself is
    // interactive (drag and drop, for one).
    rowAttributes?: (row: Row, index: number) => HTMLAttributes<HTMLTableRowElement>
    // Slide rows to their new place instead of swapping them outright. Only
    // worth it where the order is the point, as in a reorderable list.
    animateRows?: boolean
  } & HTMLTableAttributes

  let {
    id,
    caption,
    cols,
    rows,
    itemCount,
    maxRowsPerPage = $bindable(0),
    currentPage = $bindable(0),
    orderingCol = $bindable(),
    orderingMethod = $bindable(),
    search = $bindable(),
    searchLabel = m['words.search'](),
    hideCaption = false,
    cell,
    headerLeft,
    headerRight,
    rowAttributes,
    animateRows = false,
    class: classes,
    ...props
  }: TableProps = $props()

  const reduceMotion = browser && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const flipDuration = $derived(animateRows && !reduceMotion ? 200 : 0)

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
    currentPage = 0
  }

  const displayedRows = $derived(
    !itemCount && maxRowsPerPage
      ? rows.slice(currentPage * maxRowsPerPage, currentPage * maxRowsPerPage + maxRowsPerPage)
      : rows
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

    // The window is not what scrolls: the app puts the page inside a
    // `max-h-screen overflow-y-auto` main element. Listening to the window
    // alone left the offset frozen at whatever it was when the last window
    // scroll happened, which parks the header in the middle of the table on
    // top of a row. Capture phase catches the scroll from whichever ancestor
    // actually moves.
    document.addEventListener('scroll', onscroll, true)
    return () => document.removeEventListener('scroll', onscroll, true)
  })
</script>

<svelte:window onresize={() => updateGradientDisplay()} />

<div class={['fr-table', { 'fr-table--no-caption': hideCaption }, classes]}>
  <div class="fr-table__header mb-4 gap-5 md:flex-row md:flex-wrap flex flex-col">
    <div class="gap-5 flex flex-wrap items-center">
      {@render headerLeft?.()}
    </div>

    <div class="gap-5 md:flex-row md:items-center flex flex-col">
      {@render headerRight?.()}

      {#if search !== undefined}
        <Search
          id="{id}-table-search"
          bind:value={search}
          label={searchLabel}
          class="md:w-auto mb-0! ms-auto w-full"
        />
      {/if}

      {#if scrollable.left || scrollable.right}
        <div class="gap-2 md:w-auto flex w-full justify-between">
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
            class="md:ms-0 ms-auto"
            onclick={() => scrollTable(1)}
          />
        </div>
      {/if}
    </div>
  </div>

  <div class="fr-table__wrapper relative">
    <div
      class={[
        'table-gradient inset-0 md:start-[95%] absolute start-[80%] z-3',
        { hidden: !scrollable.right }
      ]}
    ></div>

    <div
      bind:this={containerElem}
      class="fr-table__container overflow-y-hidden!"
      onscroll={() => updateGradientDisplay()}
    >
      <div class="fr-table__content">
        <table {id} {...props}>
          <caption>{caption}</caption>

          <thead bind:this={stickyElem} class="relative z-2">
            <tr>
              {#each cols as col (col.id)}
                <!-- aria-sort belongs on the header cell: on the button it is
                     ignored, and the sort state is never announced. -->
                <th
                  scope="col"
                  aria-sort={col.orderable
                    ? col.id === orderingCol
                      ? orderingMethod
                      : 'none'
                    : undefined}
                  class={col.colHeaderClass}
                >
                  <div class="text-xs font-medium text-dark-grey! flex items-center">
                    <span>{@html sanitize(col.label)}</span>
                    {#if col.tooltip}
                      <Tooltip id="{id}-{col.id}" text={col.tooltip} size="xs" class="ms-1" />
                    {/if}
                    {#if col.orderable}
                      <Button
                        text={m['components.table.triageCol']({ col: stripTags(col.label) })}
                        icon={col.id === orderingCol && orderingMethod === 'ascending'
                          ? 'sort-asc'
                          : 'sort-desc'}
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
              <tr
                id="{id}-{row.id}"
                data-row-key={i}
                {...rowAttributes?.(row, i)}
                animate:flip={{ duration: flipDuration }}
              >
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

  {#if maxRowsPerPage && rows.length}
    <div class="fr-table__footer">
      <div class="fr-table__footer--start">
        <Select
          bind:selected={maxRowsPerPage}
          id="{id}-max-row-select"
          options={maxRowsOptions}
          label={m['components.table.linePerPage']()}
          hideLabel
        />
      </div>

      <div class="fr-table__footer--middle">
        <Pagination
          itemCount={itemCount ?? rows.length}
          bind:page={currentPage}
          maxItemPerPage={maxRowsPerPage}
        />
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

  .table-gradient {
    background: linear-gradient(
      90deg,
      rgba(255, 255, 255, 0) 0%,
      rgba(135, 135, 135, 0.15) 50%,
      rgba(135, 135, 135, 0.2) 100%
    );
  }
</style>
