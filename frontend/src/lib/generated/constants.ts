export const SIZE_CLASSES = ['XS', 'S', 'M', 'L', 'XL'] as const
export const ENERGY_CLASSES = ['A', 'B', 'C', 'D', 'E', 'F'] as const
export const ARCHS = ['moe', 'dense', 'matformer', 'na'] as const
export const MAYBE_ARCHS = ['maybe-moe', 'maybe-dense', 'maybe-matformer'] as const
export type SizeClasses = (typeof SIZE_CLASSES)[number]
export type EnergyClasses = (typeof ENERGY_CLASSES)[number]
export type Archs = (typeof ARCHS)[number]
export type MaybeArchs = (typeof MAYBE_ARCHS)[number]
