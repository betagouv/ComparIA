<script lang="ts">
  import { tick, type Snippet } from 'svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    id,
    label = 'Options',
    variant = 'normal',
    closeOnSelect = false,
    role = null,
    children,
    ...props
  }: {
    id: string
    label?: string
    closeOnSelect?: boolean
    variant?: 'light' | 'normal'

    role?: 'menu' | null
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
      getFocusableItems()[0]?.focus()
    }
  }

  function close(focusButton = true): void {
    open = false
    if (focusButton) buttonEl?.focus()
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
</script>

<svelte:window onpointerdown={handleWindowPointerDown} />

<div class="dropdown relative inline-block">
  <button
    bind:this={buttonEl}
    type="button"
    aria-haspopup="true"
    aria-expanded={open}
    aria-controls={id}
    class={['fr-select', { 'not-hover:bg-white': variant === 'light' }]}
    onclick={toggle}
  >
    {label}
  </button>

  {#if open}
    <div
      bind:this={contentEl}
      {id}
      {role}
      aria-label={label}
      onkeydown={handleContentKeydown}
      onclick={handleContentClick}
      {...props}
      class={['dropdown-content left-0 shadow-lg bg-white p-3 absolute z-50', props.class]}
    >
      {@render children?.()}
    </div>
  {/if}
</div>

<style lang="postcss">
  .fr-select {
    --border-plain-grey: var(--blue-france-main-525);
    --background-contrast-grey: var(--blue-ecume-975-75);
  }

  .dropdown-content {
    top: calc(100% + 0.25rem);
  }
</style>
