import type { ToolPublic } from '$lib/generated/backend'

export const globalContext = async (
  importOriginal: <T>() => Promise<T>,
  mocks?: Record<'tools', ToolPublic[]>
) => {
  const original = await importOriginal<typeof import('$lib/global.svelte')>()
  return {
    ...original,
    getToolsContext: () => original._createToolsContext(() => mocks?.tools || [])
  }
}
