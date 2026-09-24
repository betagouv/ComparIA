import type { MySurveyAnswer, PublicSurveyQuestion } from '$lib/generated/backend'
import { profileQuestions, requiredErrors } from '$lib/survey'
import { describe, expect, it } from 'vitest'

const question = (id: string, required = false): PublicSurveyQuestion => ({
  id,
  key: id,
  required,
  input_type: 'select',
  label: `Question ${id}`,
  revision: 1,
  options: [
    { key: `${id}-a`, label: 'A' },
    { key: `${id}-b`, label: 'B' }
  ]
})

const answer = (id: string, selected: string[], extra: Partial<MySurveyAnswer> = {}) => ({
  question_id: id,
  question_key: id,
  label: `Question ${id}`,
  input_type: 'select' as const,
  options: [
    { key: `${id}-a`, label: 'A' },
    { key: `${id}-b`, label: 'B' },
    { key: `${id}-old`, label: 'Old', archived: true }
  ],
  selected_keys: selected,
  ...extra
})

describe('profileQuestions', () => {
  it('adds the questions answered outside the signup form', () => {
    const listed = profileQuestions([question('signup')], [answer('vote', ['vote-a'])])

    expect(listed.map((q) => q.id)).toEqual(['signup', 'vote'])
    // An archived option nobody holds is not offered.
    expect(listed[1].options.map((o) => o.key)).toEqual(['vote-a', 'vote-b'])
  })

  it('leaves out archived questions', () => {
    const listed = profileQuestions([], [answer('gone', ['gone-a'], { archived: true })])

    expect(listed).toEqual([])
  })

  it('keeps an archived option on the question that holds it', () => {
    const listed = profileQuestions([question('signup')], [answer('signup', ['signup-old'])])

    expect(listed[0].options.map((o) => o.key)).toEqual(['signup-a', 'signup-b', 'signup-old'])
  })
})

describe('requiredErrors', () => {
  it('flags required questions left blank, whatever their shape', () => {
    const questions = [question('select', true), question('group', true), question('optional')]

    expect(
      Object.keys(requiredErrors({ select: null, group: [], optional: null }, questions))
    ).toEqual(['select', 'group'])
    expect(requiredErrors({ select: 'select-a', group: ['group-a'] }, questions)).toEqual({})
  })
})
