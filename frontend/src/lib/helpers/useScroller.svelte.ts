export type ScrollState = {
  x: number
  y: number
  maxX: number
  maxY: number
}

export function useScroller() {
  let state = $state<ScrollState>({ x: 0, y: 0, maxX: 0, maxY: 0 })
  const isAtTop = $derived(state.y <= 1)
  const isAtBottom = $derived(state.maxY - state.y <= 1)
  const canScroll = $derived(state.maxX > 1 || state.maxY > 1)

  let element: HTMLElement | undefined

  function update() {
    if (!element) return
    state = {
      x: element.scrollLeft,
      y: element.scrollTop,
      maxX: Math.max(0, element.scrollWidth - element.clientWidth),
      maxY: Math.max(0, element.scrollHeight - element.clientHeight)
    }
  }

  function attach(node: HTMLElement) {
    element = node
    node.addEventListener('scroll', update, { passive: true })
    const resizeObserver = new ResizeObserver(update)
    resizeObserver.observe(node?.firstElementChild || node)
    update()

    return () => {
      node.removeEventListener('scroll', update)
      resizeObserver.disconnect()
      if (element === node) element = undefined
    }
  }

  return {
    get canScroll() {
      return canScroll
    },
    get isAtTop() {
      return isAtTop
    },
    get isAtBottom() {
      return isAtBottom
    },
    scrollToTop() {
      element?.scrollTo({ top: 0, behavior: 'smooth' })
    },
    scrollToBottom() {
      element?.scrollTo({ top: element.scrollHeight, behavior: 'smooth' })
    },
    attach
  }
}
