/**
 * MOCKUP HELPER — product-direction prototype for the redesigned model card.
 *
 * The new card is built almost entirely from STRUCTURED fields (params, arch,
 * license, distribution, consumption…) plus STATIC UI labels, instead of the
 * per-model free-text (`desc` / `size_desc` / `fyi`) that has to be translated
 * for every model in every language.
 *
 * A few criteria shown in the target design don't exist in the data model yet
 * (context window, training-data openness, editor country, EU hosting, ranking
 * tier, external sources). For this mockup we derive or deterministically fake
 * them here so every card looks complete. Replace with real fields before
 * shipping; the per-model strings would never need translation.
 */
import type { BotModel } from './models'

export type EnergyClass = 'A' | 'B' | 'C' | 'D' | 'E' | 'F'

/** Deterministic, stable pseudo-random seed from the model id. */
function hashString(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (h << 5) - h + s.charCodeAt(i)
    h |= 0
  }
  return Math.abs(h)
}

/** Editor country of origin — FAKE map for the mockup. */
const COUNTRY_BY_ORG: Record<string, { code: string; flag: string }> = {
  'Mistral AI': { code: 'FR', flag: '🇫🇷' },
  EuroLLM: { code: 'EU', flag: '🇪🇺' },
  jpacifico: { code: 'FR', flag: '🇫🇷' },
  'Swiss AI': { code: 'CH', flag: '🇨🇭' },
  Cohere: { code: 'CA', flag: '🇨🇦' },
  DeepSeek: { code: 'CN', flag: '🇨🇳' },
  Alibaba: { code: 'CN', flag: '🇨🇳' },
  'Moonshot AI': { code: 'CN', flag: '🇨🇳' },
  Zhipu: { code: 'CN', flag: '🇨🇳' },
  MiniMax: { code: 'CN', flag: '🇨🇳' },
  '01-ai': { code: 'CN', flag: '🇨🇳' },
  AI21: { code: 'IL', flag: '🇮🇱' },
  Ordbogen: { code: 'DK', flag: '🇩🇰' }
}

/** Wh / 1M tokens → energy class. Thresholds tuned to the current catalog spread. */
function consumptionToClass(consumption: number): EnergyClass {
  if (consumption <= 80) return 'A'
  if (consumption <= 120) return 'B'
  if (consumption <= 180) return 'C'
  if (consumption <= 280) return 'D'
  if (consumption <= 450) return 'E'
  return 'F'
}

export type Tier = 'I' | 'II' | 'III' | 'IV' | 'V'

function rankToTier(rank: number): Tier {
  if (rank <= 5) return 'I'
  if (rank <= 15) return 'II'
  if (rank <= 30) return 'III'
  if (rank <= 45) return 'IV'
  return 'V'
}

/** Plausible context-window sizes — FAKE, deterministic per model. */
const CONTEXT_WINDOWS = [32_000, 128_000, 200_000, 256_000, 1_000_000]

export type Modality = 'text' | 'image' | 'audio' | 'video'

export type HardwareTier = 'smartphone' | 'laptop' | 'workstation' | 'server'

export type EnergyNote = { positive: boolean; label: string }

/**
 * What machine is needed to run the model, from its memory footprint.
 * A single escalating axis (increasing hardware), no device/location mixing:
 * personal devices (no GPU) → 1 GPU → multiple GPUs.
 */
function ramToHardware(ramGb: number, gpuCount: number): HardwareTier {
  if (ramGb <= 3) return 'smartphone'
  if (ramGb <= 16) return 'laptop'
  if (gpuCount <= 1) return 'workstation'
  return 'server'
}

/** Knowledge cutoff — FAKE, derived as ~6 months before the release date. */
function cutoffFromRelease(release: string): string | null {
  const [mm, yyyy] = release.split('/').map(Number)
  if (!mm || !yyyy) return null
  const d = new Date(yyyy, mm - 1, 1)
  d.setMonth(d.getMonth() - 6)
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`
}

export function getModelExtras(model: BotModel) {
  const seed = hashString(model.id)
  const openWeights = model.distribution !== 'api-only'
  const fullyOpen = model.distribution === 'fully-open-source'
  const isMoe = model.arch === 'moe' || model.arch === 'maybe-moe'

  // ---- Technical characteristics ----
  const contextWindow = CONTEXT_WINDOWS[seed % CONTEXT_WINDOWS.length] // FAKE
  const contextChars = contextWindow * 4 // rough tokens→chars heuristic

  // Input modalities — FAKE, deterministic. Text always; image on ~2/3 of models;
  // audio / video rarer.
  const inputModalities: Modality[] = ['text']
  if (seed % 3 !== 0) inputModalities.push('image')
  if (seed % 7 === 0) inputModalities.push('audio')
  if (seed % 11 === 0) inputModalities.push('video')

  const knowledgeCutoff = cutoffFromRelease(model.release_date) // FAKE

  // ---- Environmental impact ----
  const ramGb = model.required_ram || 16
  const gpuCount = Math.max(1, Math.ceil(ramGb / 80)) // ~80 GB / GPU
  const hardware = ramToHardware(ramGb, gpuCount)
  const energyClass = consumptionToClass(model.consumption)
  const energyNotes: EnergyNote[] = []
  if (isMoe) energyNotes.push({ positive: true, label: "mélange d'experts" })
  if (model.friendly_size === 'XL') energyNotes.push({ positive: false, label: 'très grand modèle' })
  else if (model.friendly_size === 'XS' || model.friendly_size === 'S')
    energyNotes.push({ positive: true, label: 'modèle compact' })
  if (model.quantization) energyNotes.push({ positive: true, label: 'modèle quantifié' })
  if (energyNotes.length === 0) energyNotes.push({ positive: false, label: 'architecture dense' })

  // ---- Openness & sovereignty ----
  const country = COUNTRY_BY_ORG[model.organisation] ?? { code: 'US', flag: '🇺🇸' } // FAKE
  const euHosting = country.code === 'FR' || country.code === 'EU' || fullyOpen || seed % 2 === 0 // FAKE

  // ---- Ranking performance (real when available, mock fallback) ----
  const rank = model.data?.rank ?? (seed % 40) + 1
  const totalRanked = 47 // FAKE total number of ranked models for the demo
  const votes = model.data?.n_match ?? 500 + (seed % 6000)
  const tier = rankToTier(rank)
  // Bradley-Terry score (the arena rating) + half confidence interval.
  const btScore = model.data?.elo
    ? Math.round(model.data.elo)
    : Math.max(900, 1300 - rank * 6 + (seed % 21) - 10)
  const btInterval = model.data
    ? Math.max(1, Math.round((model.data.score_p97_5 - model.data.score_p2_5) / 2))
    : 8 + (seed % 12)

  return {
    contextWindow,
    contextChars,
    inputModalities,
    knowledgeCutoff,
    gpuCount,
    hardware,
    energyClass,
    energyNotes,
    openWeights,
    fullyOpen,
    weights: openWeights ? 'publics' : 'privés',
    weightsPositive: openWeights,
    reuseLabel: model.reuse ? 'autorisée' : 'interdite',
    reusePositive: !!model.reuse,
    commercialLabel:
      model.commercial_use === null ? 'non précisé' : model.commercial_use ? 'autorisé' : 'interdit',
    commercialPositive: model.commercial_use === true,
    trainingDataLabel: fullyOpen ? 'publics' : 'privés', // FAKE for non fully-open
    trainingDataPositive: fullyOpen,
    trainingCodeLabel: fullyOpen ? 'public' : 'privé', // FAKE for non fully-open
    trainingCodePositive: fullyOpen,
    licenseLabel: model.license === 'proprietary' ? 'propriétaire' : model.license,
    country,
    euHosting,
    hasRealRanking: !!model.data,
    tier,
    rank,
    totalRanked,
    btScore,
    btInterval,
    votes,
    sources: {
      huggingface: openWeights ? `https://huggingface.co/${model.organisation}` : null, // FAKE url
      official: model.url ?? null,
      modelCard: model.url ?? null, // FAKE
      artificialAnalysis: 'https://artificialanalysis.ai/' // FAKE
    }
  }
}

export type ModelExtras = ReturnType<typeof getModelExtras>
