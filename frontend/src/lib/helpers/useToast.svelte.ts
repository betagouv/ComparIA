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
  items: []
})

export function useToast(text: string, duration: number, variant?: ToastItem['variant']) {
  toasts.items.push({ id: count++, text, duration, variant })
}

export function removeToast(id: number) {
  toasts.items = toasts.items.filter((toast) => toast.id !== id)
}
