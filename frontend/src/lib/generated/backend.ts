/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export interface ComparisonPublic {
  id: string;
  mode: "random" | "big-vs-small" | "small-models" | "custom";
  custom_models_selection: string[] | null;
  error: ErrorDetails | null;
  turns: TurnPublic[];
  revealed: boolean;
  reveal_data?: RevealData | null;
  llm_id_a: string | null;
  llm_id_b: string | null;
  system_msg_a?: string | null;
  system_msg_b?: string | null;
}
export interface ErrorDetails {
  message: string;
  pos?: ("a" | "b") | null;
  is_timeout?: boolean;
  [k: string]: unknown;
}
export interface TurnPublic {
  id: string;
  user_msg: UserMessageRead;
  choice: ("both_good" | "both_bad" | "a_better" | "b_better" | "idk") | null;
  llm_msg_a: LLMMessageCreate | null;
  keyword_annotations_a: string[];
  custom_annotation_a?: string | null;
  llm_msg_b: LLMMessageCreate | null;
  keyword_annotations_b: string[];
  custom_annotation_b?: string | null;
  [k: string]: unknown;
}
export interface UserMessageRead {
  id?: string;
  created_at?: string;
  role?: "user";
  content: string;
  web_search_results?: LinkupSearchTextResult[] | null;
  turn_id?: string | null;
  user_content: string;
  [k: string]: unknown;
}
/**
 * A text result from a Linkup search.
 *
 * Attributes:
 *     type: The type of the search result, in this case "text".
 *     name: The name of the search result.
 *     url: The URL of the search result.
 *     content: The text of the search result.
 *     favicon: The favicon URL of the search result, if available.
 */
export interface LinkupSearchTextResult {
  type: "text";
  name: string;
  url: string;
  content: string;
  favicon?: string;
  [k: string]: unknown;
}
export interface LLMMessageCreate {
  id?: string;
  role?: "assistant";
  created_at?: string | null;
  responded_at?: string | null;
  updated_at?: string | null;
  content?: string;
  reasoning_content?: string | null;
  generation_id?: string | null;
  tokens?: number | null;
  is_cached?: boolean;
  [k: string]: unknown;
}
export interface RevealData {
  b64: string;
  chosen_llm: ("a" | "b") | null;
  a: RevealModelData;
  b: RevealModelData;
  [k: string]: unknown;
}
export interface RevealModelData {
  llm_id: string;
  conso: Consumption;
  [k: string]: unknown;
}
export interface Consumption {
  tokens: number;
  input_tokens: number;
  total_tokens: number;
  co2_kg: number;
  energy_mwh: number;
  energy_kwh: number;
  [k: string]: unknown;
}
export interface LLMList {
  data_timestamp: number | null;
  models: APILLMData[];
  style_coefficients: {
    [k: string]: number;
  } | null;
  currency: CurrencyInfo;
}
/**
 * LLM data used for LLM list, sent to clients.
 * !Warning: make sure there's no secrets.
 */
export interface APILLMData {
  id?: string;
  created_at?: string;
  updated_at?: string;
  status: "enabled" | "archived";
  name: string;
  /**
   * (legacy id), usually the LLM id specified in 'api_model_id'
   */
  human_id: string;
  /**
   * Complete identifier used for API calls.
   */
  api_model_id: string | null;
  /**
   * The LLM's endpoint information, create it first if not already available
   */
  endpoint_id: string | null;
  /**
   * Apply rate limits (usually for high API costs LLMs).
   */
  rate_limited: boolean;
  /**
   * The lab that developed the LLM, create it first if not already available
   */
  lab_id: string;
  release_date: string;
  /**
   * Date after which the LLM no longer has knowledge.
   */
  knowledge_cutoff?: string | null;
  /**
   * The LLM's license, create it first if not already available
   */
  license_id: string;
  /**
   * Whether the LLM weights are public.
   */
  public_weights: boolean;
  /**
   * Whether the LLM training data is public.
   */
  public_training_data: boolean;
  /**
   * Whether the LLM training code is public.
   */
  public_training_code: boolean;
  /**
   * Whether the LLM is hostable in the EU.
   */
  eu_hostable: boolean;
  /**
   * LLM architecture, Use `maybe-*` if information is not confirmed.
   */
  arch: "moe" | "matformer" | "dense" | "maybe-moe" | "maybe-matformer" | "maybe-dense" | "na";
  /**
   * Total parameters in billions.
   */
  params: number;
  /**
   * Active parameters in billions (only for MoE LLMs).
   */
  active_params: number | null;
  /**
   * Size of its context window in tokens.
   */
  context_tokens: number | null;
  /**
   * Quantization scheme applied (q4, q8, or None for full precision).
   */
  quantization: ("q4" | "q8") | null;
  /**
   * What kind of media the LLM can have in input.
   */
  inputs: ("text" | "image" | "audio" | "video")[];
  /**
   * Price per million input tokens in $.
   */
  price_in: number;
  /**
   * Price per million output tokens in $.
   */
  price_out: number;
  /**
   * System message to add in llm call if specified
   */
  system_prompt: string | null;
  /**
   * List of links to display in LLM card.
   */
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
  /**
   * Licence name (e.g. 'Apache 2.0' or 'MIT').
   */
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
  /**
   * An icon name from https://lobehub.com/fr/icons or a filename (e.g. 'ai2.svg') from `frontend/static/orgs/ai/`.
   */
  logo: string;
  /**
   * A 2 letter code from https://en.wikipedia.org/wiki/ISO_3166-1.
   */
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
 *     positive_prefs_ratio: Share of positive tags, null when the model has
 *         no tagged votes or the instance has turned off a whole side
 *     total_prefs: Total number of preference votes received
 *     counts: Count per vote tag key, including keys no longer offered
 */
export interface PreferencesData {
  positive_prefs_ratio: number | null;
  total_prefs: number;
  counts: {
    [k: string]: number;
  };
  [k: string]: unknown;
}
export interface CurrencyInfo {
  code: string;
  rate_from_eur: number;
  date: string | null;
  source: "base" | "frankfurter" | "manual";
  [k: string]: unknown;
}
/**
 * What the profile page and the personal-data export show.
 */
export interface MySurveyAnswer {
  question_id: string;
  question_key: string;
  label: string;
  input_type: "select" | "checkbox_group";
  options: PublicSurveyOption[];
  selected_keys: string[];
}
export interface PublicSurveyOption {
  key: string;
  label: string;
}
export interface MySurveyAnswersResponse {
  answers: MySurveyAnswer[];
}
export interface PublicLegalDocument {
  version: string;
  content_hash: string;
  locale: string;
  content: string;
  published_at: string;
  effective_at: string;
}
export interface PublicSurveyQuestion {
  id: string;
  key: string;
  required: boolean;
  input_type: "select" | "checkbox_group";
  label: string;
  revision: number;
  options: PublicSurveyOption[];
}
export interface PublicSurveyQuestionsResponse {
  questions: PublicSurveyQuestion[];
}
export interface PublicVoteTag {
  key: string;
  sign: "positive" | "negative";
  emoji: string;
  reserved: boolean;
  label?: string | null;
}
export interface PublicVoteTagsResponse {
  tags: PublicVoteTag[];
}
export interface SurveyAnswerSubmit {
  answers: SurveyQuestionAnswer[];
}
export interface SurveyQuestionAnswer {
  question_id: string;
  option_keys: string[];
}
/**
 * Closing the popup and declining it are the same thing: both count as one
 * of the three showings and neither is a special case worth a column.
 */
export interface SurveyDismiss {
  question_ids: string[];
}
