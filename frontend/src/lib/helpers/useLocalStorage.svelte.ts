import { browser } from '$app/environment'

export function useLocalStorage<T>(
  key: string,
  initialValue: T,
  validator?: (value: T) => T
): { value: T } {
  function getInitialValue(): T {
    if (!browser) return initialValue
    let v = localStorage.getItem(key)
    if (v === null) return initialValue
    v = typeof initialValue === 'string' ? v : JSON.parse(v)
    if (typeof v !== typeof initialValue) return initialValue
    if (validator) return validator(v as T)
    return v as T
  }

  const value = $state<{ value: T }>({ value: getInitialValue() })

  $effect(() => {
    if (browser) {
      const v =
        typeof initialValue !== 'string' ? JSON.stringify(value.value) : (value.value as string)
      localStorage.setItem(key, v)
    }
  })

  return value
}
