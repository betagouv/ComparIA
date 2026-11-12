<script lang="ts">
  import { tick, type Snippet } from 'svelte'
  import type { ClassValue, SvelteHTMLElements } from 'svelte/elements'

  let {
    id,
    label = 'Options',
    variant = 'normal',
    closeOnSelect = false,
    role = null,
    disabled = false,
    maxHeight = 400,
    buttonClass = 'fr-select',
    buttonLabel,
    onClose,
    contentSnippet,
    children,
    ...props
  }: {
    id: string
    label?: string
    closeOnSelect?: boolean
    variant?: 'light' | 'normal'
    role?: 'menu' | null
    disabled?: boolean
    maxHeight?: number
    buttonClass?: ClassValue
    buttonLabel?: Snippet<[string]>
    onClose?: () => void
    contentSnippet?: Snippet<[close: (focusButton?: boolean) => void]>
    children?: Snippet
  } & SvelteHTMLElements['div'] = $props()

  let open = $state(false)
  let buttonEl = $state<HTMLButtonElement>()
  let contentEl = $state<HTMLDivElement>()

  function getFocusableItems(): HTMLElement[] {
    if (!contentEl) return []
    return Array.from(
      contentEl.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    )
  }

  async function toggle(): Promise<void> {
    open = !open
    if (open) {
      await tick()
      await tick()
      getFocusableItems()[0]?.focus()
    }
  }

  function close(focusButton = true): void {
    open = false
    if (focusButton) buttonEl?.focus()
    onClose?.()
  }

  function handleContentKeydown(e: KeyboardEvent): void {
    const items = getFocusableItems()
    if (items.length === 0) return

    const currentIndex = items.indexOf(document.activeElement as HTMLElement)

    switch (e.key) {
      case 'ArrowDown': {
        e.preventDefault()
        items[(currentIndex + 1) % items.length].focus()
        break
      }
      case 'ArrowUp': {
        e.preventDefault()
        items[(currentIndex - 1 + items.length) % items.length].focus()
        break
      }
      case 'Home':
        e.preventDefault()
        items[0].focus()
        break
      case 'End':
        e.preventDefault()
        items[items.length - 1].focus()
        break
      case 'Escape':
        e.preventDefault()
        close()
        break
      case 'Tab':
        close(false)
        break
    }
  }

  function handleWindowPointerDown(e: PointerEvent): void {
    if (!open) return
    const target = e.target as Node
    if (!contentEl?.contains(target) && !buttonEl?.contains(target)) {
      close(false)
    }
  }

  function handleContentClick(e: MouseEvent): void {
    const target = e.target as HTMLElement
    if (closeOnSelect && target.closest('[role="menuitem"], button, a')) {
      close()
    }
  }

  let contentStyle = $state<Record<string, string>>({})
  let isBelow = $state(true)

  function calculatePosition() {
    if (!buttonEl || !contentEl) return
    let offset = 4

    const { left, top, right, bottom, width: btnWidth } = buttonEl.getBoundingClientRect()
    const contentWidth = contentEl.scrollWidth
    const { innerWidth, innerHeight } = window

    // A list longer than maxHeight scrolls inside it. It opens on the side
    // with room for it, else on the side with more room, and scrolls within
    // that room so its end never goes off screen.
    const wanted = Math.min(contentEl.scrollHeight, maxHeight)
    const roomBelow = innerHeight - bottom - offset * 2
    const roomAbove = top - offset * 2
    isBelow = roomBelow >= wanted || roomBelow >= roomAbove
    const contentHeight = Math.min(wanted, Math.max(isBelow ? roomBelow : roomAbove, 0))
    let topPos = isBelow ? bottom + offset : top - contentHeight - offset

    // Clamp top to viewport
    if (topPos + contentHeight > innerHeight - offset) {
      topPos = innerHeight - contentHeight - offset
    }
    topPos = Math.max(topPos, offset)

    // Horizontal pos
    let leftPos = left
    const maxWidth = Math.max(contentWidth, btnWidth)
    const rightEdge = leftPos + maxWidth

    // Flip to right-aligned
    if (rightEdge > innerWidth - offset) {
      leftPos = right - maxWidth
    }

    // Clamp left to viewport
    if (leftPos + maxWidth > innerWidth - offset) {
      leftPos = innerWidth - maxWidth - offset
    }
    leftPos = Math.max(leftPos, offset)

    contentStyle = {
      top: `${topPos}px`,
      left: `${leftPos}px`,
      'min-width': `${btnWidth}px`,
      'max-width': `${innerWidth - offset * 2}px`,
      'max-height': `${contentHeight}px`
    }
  }

  function updatePosition() {
    if (open) calculatePosition()
  }

  $effect(() => {
    if (open) {
      tick().then(calculatePosition)

      // Update on scroll and resize
      window.addEventListener('scroll', updatePosition, { passive: true, capture: true })
      window.addEventListener('resize', updatePosition, { passive: true })

      return () => {
        window.removeEventListener('scroll', updatePosition, { capture: true })
        window.removeEventListener('resize', updatePosition)
      }
    } else {
      contentStyle = {}
    }
  })

  const style = $derived(
    Object.entries(contentStyle)
      .map(([k, v]) => `${k}: ${v};`)
      .join(' ')
  )
</script>

<svelte:window onpointerdown={handleWindowPointerDown} />

<div class="dropdown relative inline-block">
  <button
    bind:this={buttonEl}
    type="button"
    aria-haspopup={role ?? true}
    aria-expanded={open}
    aria-controls={id}
    {disabled}
    class={[buttonClass, { 'not-hover:bg-white disabled:bg-white': variant === 'light' }]}
    onclick={toggle}
  >
    {#if buttonLabel}{@render buttonLabel(label)}{:else}{label}{/if}
  </button>

  <div
    bind:this={contentEl}
    {id}
    {role}
    aria-label={label}
    onkeydown={handleContentKeydown}
    onclick={handleContentClick}
    {...props}
    class={[
      'dropdown-content ease-in rounded-sm left-0 shadow-lg bg-white fixed z-50 overflow-y-auto transition-opacity transition-transform duration-100',
      { 'invisible scale-98 opacity-0': !open, 'translate-y-0 scale-100': open },
      !open ? (isBelow ? '-translate-y-1' : 'translate-y-1') : '',
      props.class
    ]}
    {style}
  >
    {@render contentSnippet?.(close)}
    {@render children?.()}
  </div>
</div>

<style lang="postcss">
  .fr-select {
    --border-plain-grey: var(--blue-france-main-525);
    --background-contrast-grey: var(--blue-ecume-975-75);
  }
</style>
