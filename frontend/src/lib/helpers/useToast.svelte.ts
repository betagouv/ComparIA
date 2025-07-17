export type ToastItem = {
  id: number
  text: string
  duration: number
  variant?: 'primary' | 'error'
}

let count = $state(10)

export const toasts = $state<{
  items: ToastItem[]
}>({
  items: [
    { id: 0, text: 'Lien copié dans le presse-papiers', duration: 10000 },
    { id: 1, text: 'Il n\'est pas possible de réessayer, veuillez recharger la page.', variant: 'error', duration: 10000 },
    { id: 2, text: 'adad', duration: 1000 }
  ]
})

export function useToast(text: string, duration: number, variant?: ToastItem['variant']) {
  toasts.items.push({ id: count++, text, duration, variant })
}

export function removeToast(id: number) {
  toasts.items = toasts.items.filter((toast) => toast.id !== id)
}
