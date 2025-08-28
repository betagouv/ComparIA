import type { Attachment } from "svelte/attachments"

export function teleport(containerId: string): Attachment {
  return (element) => {
    const teleportContainer = document.getElementById(containerId)
    teleportContainer?.appendChild(element)
    
    return () => element.remove()
  }
}

export const scrollTo: Attachment = (element) => {
  element.scrollIntoView({ behavior: 'smooth' })
}