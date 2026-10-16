import fr from '../../locales/messages/fr.json'
import { describe, expect, it } from 'vitest'

type Tree = { [key: string]: string | Tree }

function strings(tree: Tree, path: string): [string, string][] {
  return Object.entries(tree).flatMap(([key, value]) =>
    typeof value === 'string' ? [[`${path}.${key}`, value]] : strings(value, `${path}.${key}`)
  )
}

describe('French copy of the limits', () => {
  // As the rest of the French copy: "n’en choisissez qu’un", "C’est parti".
  it.each(['arene.limits', 'arene.apiErrors.send_failed', 'admin.limits'])(
    'writes apostrophes as ’ in %s',
    (path) => {
      const node = path.split('.').reduce<Tree | string>((n, k) => (n as Tree)[k], fr as Tree)
      const values = typeof node === 'string' ? [[path, node]] : strings(node, path)
      expect(values.filter(([, value]) => value.includes("'"))).toEqual([])
    }
  )
})
