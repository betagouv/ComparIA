import type { ActivityConversationRow } from '$lib/generated/admin'
import { m } from '$lib/i18n/messages'

// The `detail` of the 409 answering a release the partner may already have,
// see backend/errors.py. Any other 409 on a reservation carries a ReserveBlock.
export const PARTNER_HAS_IT = 'partner_has_it'

export type ReserveBlock = NonNullable<ActivityConversationRow['reserve_block']>

// Why a comparison cannot be reserved, as utils/dataset/reservation.py names it.
const RESERVE_BLOCKS: Record<ReserveBlock, () => string> = {
  publishing: () => m['admin.activity.reserveBlocks.publishing'](),
  published: () => m['admin.activity.reserveBlocks.published'](),
  pii: () => m['admin.activity.reserveBlocks.pii'](),
  cohort: () => m['admin.activity.reserveBlocks.cohort'](),
  analysis_failed: () => m['admin.activity.reserveBlocks.analysis_failed']()
}

export function isReserveBlock(detail: unknown): detail is ReserveBlock {
  return typeof detail === 'string' && detail in RESERVE_BLOCKS
}

export const reserveBlockLabel = (block: ReserveBlock) => RESERVE_BLOCKS[block]()
