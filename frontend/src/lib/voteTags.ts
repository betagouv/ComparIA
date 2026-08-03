import { m } from '$lib/i18n/messages'
import { createContext } from 'svelte'

export type VoteTagSign = 'positive' | 'negative'

export type VoteTag = {
  key: string
  sign: VoteTagSign
  emoji: string
  reserved: boolean
  label?: string | null
}

export type PublicVoteTags = {
  tags: VoteTag[]
}

export const emptyVoteTags: PublicVoteTags = { tags: [] }

export const [getVoteTagsContext, setVoteTagsContext] = createContext<VoteTag[]>()

/**
 * The seven tags shipped with the platform are translated in the message
 * files. Tags an instance added itself carry their own label, since an admin
 * creates them long after the build.
 */
function label(tag: VoteTag, messageKey: string) {
  if (!tag.reserved) return tag.label ?? tag.key
  return (m as unknown as Record<string, () => string>)[messageKey]()
}

export function voteTagLabel(tag: VoteTag) {
  return label(tag, `vote.choices.${tag.sign}.${tag.key}`)
}

export function voteTagColLabel(tag: VoteTag) {
  return label(tag, `ranking.preferences.table.cols.${tag.key}`)
}

export function voteTagsBySign(tags: VoteTag[], sign: VoteTagSign) {
  return tags.filter((tag) => tag.sign === sign)
}
