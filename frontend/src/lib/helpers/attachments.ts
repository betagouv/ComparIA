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
