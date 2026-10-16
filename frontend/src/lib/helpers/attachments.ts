import { untrack } from 'svelte'
import type { Attachment } from 'svelte/attachments'

export function teleport(containerId: string): Attachment {
  return (element) => {
    const teleportContainer = document.getElementById(containerId)
    teleportContainer?.appendChild(element)

    return () => element.remove()
  }
}

export const scrollTo: Attachment = (element) => {
  setTimeout(() => {
    element.scrollIntoView({ behavior: 'smooth' })
  }, 100)
}

/**
 * Moves focus to the element once it shows, when `when` says so: it takes the
 * place of what the person was using. Read once, so a later change leaves
 * focus alone.
 */
export function focusOnShow(when: () => boolean): Attachment<HTMLElement> {
  return (element) => {
    if (!untrack(when)) return
    element.tabIndex = -1
    element.focus()
  }
}

/**
 * Tells `set` whether focus sits inside the element. Focus lost with a child
 * that is removed still counts as inside (some browsers send focusout then),
 * so a panel taking that child's place can take focus too.
 */
export function focusWithin(set: (inside: boolean) => void): Attachment<HTMLElement> {
  return (area) => {
    const onIn = () => set(true)
    const onOut = (e: FocusEvent) => {
      if (area.contains(e.relatedTarget as Node | null)) return
      const left = e.target as Node
      // Told apart from a removal once it is done.
      setTimeout(() => {
        if (left.isConnected) set(area.contains(document.activeElement))
      })
    }
    area.addEventListener('focusin', onIn)
    area.addEventListener('focusout', onOut)
    return () => {
      area.removeEventListener('focusin', onIn)
      area.removeEventListener('focusout', onOut)
    }
  }
}
