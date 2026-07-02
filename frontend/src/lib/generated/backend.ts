/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export interface LLMList {
  data_timestamp: number | null;
  models: APILLMData[];
  style_coefficients: {
    [k: string]: number;
  } | null;
}
/**
 * LLM data used for LLM list, sent to clients.
 * !Warning: make sure there's no secrets.
 */
export interface APILLMData {
  id?: string;
  created_at?: string;
  updated_at?: string;
  lab_id: string;
  license_id: string;
  endpoint_id: string | null;
  human_id: string;
  api_model_id: string | null;
  status: "enabled" | "archived";
  name: string;
  rate_limited: boolean;
  release_date: string;
  knowledge_cutoff: string | null;
  arch: "moe" | "matformer" | "dense" | "maybe-moe" | "maybe-matformer" | "maybe-dense" | "na";
  params: number;
  active_params: number | null;
  context_tokens: number | null;
  quantization: ("q4" | "q8") | null;
  inputs: ("text" | "image" | "audio" | "video")[];
  public_weights: boolean;
  public_training_data: boolean;
  public_training_code: boolean;
  eu_hostable: boolean;
  price_in: number;
  price_out: number;
  system_prompt: string | null;
  links?: Link[];
  license: LLMLicensePublic;
  lab: LLMLabPublic;
  data?: DatasetData | null;
  prefs?: PreferencesData | null;
  size_class: "XS" | "S" | "M" | "L" | "XL";
  required_ram: number;
  wh_per_million_token: number;
  energy_class: "A" | "B" | "C" | "D" | "E" | "F";
  [k: string]: unknown;
}
export interface Link {
  text: string;
  url: string;
  [k: string]: unknown;
}
export interface LLMLicensePublic {
  id?: string;
  created_at?: string;
  updated_at?: string;
  kind: "proprietary" | "open-weights" | "open-source";
  name: string;
  reuse: boolean;
  commercial_use: boolean;
  [k: string]: unknown;
}
export interface LLMLabPublic {
  id?: string;
  created_at?: string;
  updated_at?: string;
  name: string;
  logo: string;
  origin_country: string;
  [k: string]: unknown;
}
/**
 * Ranking/evaluation data exposed for a model.
 *
 * The top-level fields are the style-controlled ranking (Style Control on,
 * the default). ``uncontrolled`` carries the plain Bradley-Terry ranking the
 * frontend swaps in when Style Control is toggled off, so the leaderboard can
 * switch views without a recompute. It is ``None`` for models that are
 * degenerate (never won or never lost) in the plain fit.
 */
export interface DatasetData {
  elo: number;
  score_p2_5: number;
  score_p97_5: number;
  rank_p2_5: number;
  rank_p97_5: number;
  rank: number;
  n_match: number;
  mean_win_prob: number;
  win_rate: number;
  uncontrolled?: RankingVariant | null;
  /**
   * Confidence interval: [lower bound, upper bound] for ranking.
   */
  trust_range: number[];
  [k: string]: unknown;
}
/**
 * A single Bradley-Terry ranking view (one set of Elo scores and ranks).
 *
 * The leaderboard ships two of these per model: the style-controlled view
 * (shown by default) and the plain view used when the user turns Style Control
 * off. They share the raw vote count but differ in Elo, ranks and win
 * probabilities once presentation features are regressed out.
 *
 * Attributes:
 *     elo: Estimated Elo rating (median/central estimate)
 *     score_p2_5/p97_5: Confidence interval bounds (2.5th and 97.5th percentile)
 *     rank/rank_p2_5/rank_p97_5: Model ranking with confidence bounds
 *     n_match: Number of comparisons in dataset
 *     mean_win_prob: Probability model wins in random matchup
 *     win_rate: Percentage of matches won
 *     trust_range: Computed confidence interval for ranking
 */
export interface RankingVariant {
  elo: number;
  score_p2_5: number;
  score_p97_5: number;
  rank_p2_5: number;
  rank_p97_5: number;
  rank: number;
  n_match: number;
  mean_win_prob: number;
  win_rate: number;
  /**
   * Confidence interval: [lower bound, upper bound] for ranking.
   */
  trust_range: number[];
  [k: string]: unknown;
}
/**
 * User preference statistics from ComparIA voting.
 *
 * Aggregated counts of user ratings for specific quality attributes.
 *
 * Attributes:
 *     positive_prefs_ratio: Percentage of positive preferences (useful, complete, etc.)
 *     total_prefs: Total number of preference votes received
 *     useful/complete/creative/clear_formatting: Count of positive preferences
 *     incorrect/superficial/instructions_not_followed: Count of negative preferences
 */
export interface PreferencesData {
  positive_prefs_ratio: number;
  total_prefs: number;
  useful: number;
  clear_formatting: number;
  complete: number;
  creative: number;
  incorrect: number;
  instructions_not_followed: number;
  superficial: number;
  [k: string]: unknown;
}
