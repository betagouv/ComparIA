// Public MCP servers that answer without a credential, tried in live
// comparisons. A preset only fills the form: every field stays editable.
export type ToolPreset = {
  key: string
  label: string
  description: string
  url: string
  source: string
}

export const MCP_PRESETS: ToolPreset[] = [
  {
    key: 'datagouv',
    label: 'Données publiques',
    description: 'Chercher des jeux de données publics sur data.gouv.fr.',
    url: 'https://mcp.data.gouv.fr/mcp',
    source: 'data.gouv.fr'
  },
  {
    key: 'deepwiki',
    label: 'DeepWiki',
    description: 'Poser des questions sur un dépôt de code public GitHub.',
    url: 'https://mcp.deepwiki.com/mcp',
    source: 'deepwiki.com'
  },
  {
    key: 'context7',
    label: 'Context7',
    description: 'Lire la documentation à jour des bibliothèques de code.',
    url: 'https://mcp.context7.com/mcp',
    source: 'context7.com'
  },
  {
    key: 'mslearn',
    label: 'Microsoft Learn',
    description: 'Chercher dans la documentation officielle de Microsoft.',
    url: 'https://learn.microsoft.com/api/mcp',
    source: 'learn.microsoft.com'
  },
  {
    key: 'huggingface',
    label: 'Hugging Face',
    description: "Chercher des modèles, jeux de données et articles d'IA.",
    url: 'https://huggingface.co/mcp',
    source: 'huggingface.co'
  },
  {
    key: 'cloudflare_docs',
    label: 'Documentation Cloudflare',
    description: 'Chercher dans la documentation de Cloudflare.',
    url: 'https://docs.mcp.cloudflare.com/mcp',
    source: 'cloudflare.com'
  }
]

/** A key from a label: lowercase ASCII, words joined by underscores. */
export function toKey(label: string): string {
  return label
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

/** The key, with a number added when another tool already uses it. */
export function uniqueKey(base: string, taken: string[]): string {
  const key = base || 'outil'
  if (!taken.includes(key)) return key
  let n = 2
  while (taken.includes(`${key}_${n}`)) n++
  return `${key}_${n}`
}
