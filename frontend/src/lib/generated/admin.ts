/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export interface ActivityConversation {
  id: string;
  created_at: string;
  mode: string;
  cohorts: string | null;
  revealed: boolean;
  revealed_at: string | null;
  model_a: ActivityLLM | null;
  model_b: ActivityLLM | null;
  system_msg_a: string | null;
  system_msg_b: string | null;
  llm_analyzed: boolean;
  short_summary: string | null;
  keywords: string[];
  categories: string[];
  languages: string[];
  contains_pii: boolean;
  contains_spam: boolean;
  archived: boolean;
  archived_reason:
    | (
        | "corrupted_no_model"
        | "corrupted_against_self"
        | "corrupted_no_response"
        | "corrupted_response_all_none"
        | "corrupted_response_last_none"
        | "corrupted_response_some_none"
        | "corrupted_response_all_empty"
        | "corrupted_response_last_empty"
        | "corrupted_response_some_empty"
        | "corrupted_model_stream"
        | "corrupted_not_equal_length"
        | "spam"
        | "pii"
        | "unknown_llm"
        | "blacklist_grok"
        | "unknown"
      )
    | null;
  error: ErrorDetails | null;
  turns: ActivityTurn[];
  stopped?: ActivityStoppedMessage[];
}
export interface ActivityLLM {
  id: string;
  name: string;
  human_id: string;
  [k: string]: unknown;
}
export interface ErrorDetails {
  code?: ("timeout" | "context_too_long" | "empty_response" | "provider_error") | null;
  message: string;
  pos?: ("a" | "b") | null;
  is_timeout?: boolean;
  [k: string]: unknown;
}
export interface ActivityTurn {
  id: string;
  created_at: string;
  prompt: string;
  web_search_results:
    | {
        [k: string]: unknown;
      }[]
    | null;
  answer_a: ActivityAnswer | null;
  answer_b: ActivityAnswer | null;
  choice: ("both_good" | "both_bad" | "a_better" | "b_better" | "idk") | null;
  voted_at: string | null;
  tags_a: string[];
  tags_b: string[];
  comment_a: string | null;
  comment_b: string | null;
  prompt_check: ActivityPromptCheck | null;
  [k: string]: unknown;
}
export interface ActivityAnswer {
  content: string;
  reasoning_content: string | null;
  tokens: number | null;
  duration_ms: number | null;
  [k: string]: unknown;
}
export interface ActivityPromptCheck {
  decision: string;
  model: string;
  triggered: {
    [k: string]: string;
  };
  user_proceeded: boolean;
  [k: string]: unknown;
}
/**
 * A message the prompt check refused or warned about.
 */
export interface ActivityStoppedMessage {
  id: string;
  created_at: string;
  decision: string;
  user_proceeded: boolean;
  criteria: string[];
  contains_pii: boolean;
  prompt: string;
  comparison_id: string | null;
  [k: string]: unknown;
}
export interface ActivityConversationsPage {
  items: ActivityConversationRow[];
  next_cursor: string | null;
  total: number | null;
  total_capped: boolean;
}
export interface ActivityConversationRow {
  id: string;
  created_at: string;
  mode: string;
  cohorts: string | null;
  model_a: ActivityLLM | null;
  model_b: ActivityLLM | null;
  first_prompt: string;
  turns: number;
  choices: (("both_good" | "both_bad" | "a_better" | "b_better" | "idk") | null)[];
  tags_a: string[];
  tags_b: string[];
  has_comment: boolean;
  comment: string | null;
  revealed: boolean;
  categories: string[];
  llm_analyzed: boolean;
  contains_pii: boolean;
  contains_spam: boolean;
  archived: boolean;
  has_error: boolean;
  [k: string]: unknown;
}
export interface ActivityFilterOptions {
  llms: ActivityLLM[];
  modes: ActivityMode[];
  cohorts: string[];
  categories: string[];
}
export interface ActivityMode {
  key: string;
  label: string;
  [k: string]: unknown;
}
export interface ActivityOverview {
  range_start: string | null;
  range_end: string;
  bucket: "hour" | "day" | "week" | "month";
  totals: ActivityTotals;
  activity: ActivityPoint[];
  choices: {
    [k: string]: number;
  };
  modes: {
    [k: string]: number;
  };
  computed_at: string;
}
export interface ActivityTotals {
  conversations: number;
  prompts: number;
  votes: number;
  idk: number;
  comments: number;
  tagged: number;
  voted_conversations: number;
  revealed_conversations: number;
  errored_conversations: number;
  [k: string]: unknown;
}
export interface ActivityPoint {
  date: string;
  conversations: number;
  prompts: number;
  votes: number;
  partial?: boolean;
  projected_conversations?: number | null;
  projected_prompts?: number | null;
  projected_votes?: number | null;
  [k: string]: unknown;
}
export interface ActivityStoppedMessagesPage {
  items: ActivityStoppedMessage[];
  next_cursor: string | null;
}
export interface AdminLegalDocument {
  id: string;
  kind: "terms" | "privacy_policy";
  version: string;
  content: {
    [k: string]: string;
  };
  content_hash: string;
  published_at: string;
  effective_at: string;
  retired_at: string | null;
}
export interface AdminPublishDestination {
  id: string;
  name: string;
  kind: "huggingface" | "s3";
  config: HuggingFaceConfigPublic | S3ConfigPublic;
  datasets: ("normal" | "raw")[];
  enabled: boolean;
  publish_frequency: "off" | "daily" | "weekly" | "monthly";
  next_run_at?: string | null;
  request_pending_seconds?: number | null;
}
export interface HuggingFaceConfigPublic {
  kind?: "huggingface";
  repo_path: string;
  [k: string]: unknown;
}
export interface S3ConfigPublic {
  kind?: "s3";
  endpoint: string;
  bucket: string;
  region?: string | null;
  prefix?: string;
  secure?: boolean;
  [k: string]: unknown;
}
export interface AdminPublishDestinationsResponse {
  destinations: AdminPublishDestination[];
}
export interface AdminPublishRun {
  started_at: string;
  finished_at: string | null;
  succeeded: boolean | null;
  error: string | null;
  held_back: number | null;
  published: number | null;
}
export interface AdminPublishStatus {
  runs: AdminPublishRun[];
}
export interface AdminSuggestion {
  id: string;
  text: string;
  locale: "da" | "en" | "fr" | "it" | "lt" | "nb-NO" | "sv";
  category_id: string;
  category_title: string;
  status: "available" | "archived";
  created_at: string;
  updated_at: string;
}
export interface AdminSuggestionCategory {
  id: string;
  locale: "da" | "en" | "fr" | "it" | "lt" | "nb-NO" | "sv";
  key: string;
  title: string;
  description: string;
  icon: string;
  tooltip?: string | null;
  display_order: number;
  archived?: boolean;
  suggestion_count?: number;
  available_suggestion_count?: number;
}
export interface AdminSurveyOption {
  key: string;
  labels: {
    [k: string]: string;
  };
  archived: boolean;
  answer_count: number;
}
export interface AdminSurveyQuestion {
  id: string;
  key: string;
  required: boolean;
  input_type: "select" | "checkbox_group";
  labels: {
    [k: string]: string;
  };
  options: AdminSurveyOption[];
  published: boolean;
  revision: number;
  display_order: number;
  archived: boolean;
  respondent_count: number;
}
export interface AdminSurveyResponse {
  questions: AdminSurveyQuestion[];
  total_respondents: number;
}
export interface AdminVoteTag {
  id: string;
  key: string;
  sign: "positive" | "negative";
  emoji: string;
  reserved: boolean;
  labels: {
    [k: string]: string;
  } | null;
  display_order: number;
  archived: boolean;
  usage_count: number;
}
export interface AdminVoteTagsResponse {
  tags: AdminVoteTag[];
}
export interface AppSettingsPatch {
  auth_access_policy?: ("anonymous_first" | "sign_in_required") | null;
  auth_domain_allowlist?: string[] | null;
  votes_objective?: number | null;
  ranking_min_votes?: number | null;
  ranking_max_rank_spread?: number | null;
  survey_reask_after_days?: number | null;
  platform_name?: string | null;
  primary_color_light?: string | null;
  primary_color_dark?: string | null;
  secondary_color_light?: string | null;
  secondary_color_dark?: string | null;
  homepage_url?: string | null;
  enabled_locales?: ("da" | "en" | "fr" | "it" | "lt" | "nb-NO" | "sv")[] | null;
  default_locale?: ("da" | "en" | "fr" | "it" | "lt" | "nb-NO" | "sv") | null;
  analysis_endpoint_id?: string | null;
  analysis_model?: string | null;
  publish_frequency?: ("off" | "daily" | "weekly" | "monthly") | null;
  publish_hour?: number | null;
  publish_timezone?: string | null;
  auth_methods?: string[] | null;
  oidc_issuer?: string | null;
  oidc_client_id?: string | null;
  oidc_client_secret?: string | null;
  oidc_scopes?: string[] | null;
  oidc_button_label?: string | null;
}
export interface AppSettingsPublic {
  auth_access_policy: "anonymous_first" | "sign_in_required";
  auth_domain_allowlist: string[];
  votes_objective: number;
  ranking_min_votes: number;
  ranking_max_rank_spread: number;
  survey_reask_after_days: number;
  platform_name: string;
  primary_color_light: string;
  primary_color_dark: string;
  secondary_color_light: string;
  secondary_color_dark: string;
  homepage_url: string | null;
  analysis_endpoint_id: string | null;
  analysis_model: string | null;
  publish_frequency: "off" | "daily" | "weekly" | "monthly";
  publish_hour: number;
  publish_timezone: string;
  has_custom_logo: boolean;
  logo_version?: string | null;
  enabled_locales: ("da" | "en" | "fr" | "it" | "lt" | "nb-NO" | "sv")[];
  default_locale: "da" | "en" | "fr" | "it" | "lt" | "nb-NO" | "sv";
  auth_methods: string[];
  oidc_issuer: string | null;
  oidc_client_id: string | null;
  oidc_has_client_secret: boolean;
  oidc_scopes: string[];
  oidc_button_label: string | null;
  oidc_has_button_logo: boolean;
  oidc_button_logo_content_type: string | null;
  oidc_connection_test?: OIDCConnectionTest | null;
  updated_at: string;
  updated_by?: string | null;
}
/**
 * The last connection test, when it was run on the config in force.
 */
export interface OIDCConnectionTest {
  passed: boolean;
  reason?: string | null;
  tested_at: string;
  [k: string]: unknown;
}
export interface InformationalLegalPage {
  mode?: "internal" | "external";
  external_url?: string | null;
  visible_in_legal_menu?: boolean;
  visible_in_settings?: boolean;
  content_by_locale?: TranslatableAnnotatedStrFieldInfoAnnotationNoneTypeRequiredTrueMetadataMinLenMinLength1MaxLenMaxLength200000;
}
export interface TranslatableAnnotatedStrFieldInfoAnnotationNoneTypeRequiredTrueMetadataMinLenMinLength1MaxLenMaxLength200000 {
  [k: string]: string;
}
/**
 * LLM definition.
 *
 * Contains basic LLM information and links to licence, lab and endpoint.
 */
export interface LLMData {
  id?: string;
  created_at?: string;
  updated_at?: string;
  /**
   * enabled: callable and displayed in llm list + rankings; archived: not callable but displayed in llm list + rankings; disabled: not callable and hidden in llm list + rankings.
   */
  status: "archived" | "disabled" | "enabled";
  name: string;
  /**
   * (legacy id), usually the LLM id specified in 'api_model_id'
   */
  human_id: string;
  /**
   * Complete identifier used for API calls.
   */
  api_model_id?: string | null;
  /**
   * The LLM's endpoint information, create it first if not already available
   */
  endpoint_id?: string | null;
  /**
   * Apply rate limits (usually for high API costs LLMs).
   */
  rate_limited: boolean;
  /**
   * Whether visitors can pick this LLM themselves in custom mode. When off, it shows greyed out there and only comes up in random draws.
   */
  custom_selectable?: boolean;
  /**
   * Turn off for a system that brings its own retrieval or tools behind its endpoint. It is then always called without tools, even when the comparison has some, while the model it faces keeps them.
   */
  arena_tools?: boolean;
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
  active_params?: number | null;
  /**
   * Size of its context window in tokens.
   */
  context_tokens?: number | null;
  /**
   * Quantization scheme applied (q4, q8, or None for full precision).
   */
  quantization?: ("q4" | "q8") | null;
  /**
   * What kind of media the LLM can have in input.
   */
  inputs: ("text" | "image" | "audio" | "video")[];
  /**
   * Price per million input tokens in USD.
   */
  price_in: number;
  /**
   * Price per million output tokens in USD.
   */
  price_out: number;
  /**
   * System message to add in llm call if specified
   */
  system_prompt?: string | null;
  /**
   * List of links to display in LLM card.
   */
  links?: Link[];
  /**
   * Free labels such as 'legal' or 'sovereign'. Selection modes can draw only the models carrying some of them.
   */
  tags?: string[];
}
export interface Link {
  text: string;
  url: string;
  [k: string]: unknown;
}
/**
 * LLM endpoint configuration for API calls.
 */
export interface LLMEndpoint {
  id?: string;
  created_at?: string;
  updated_at?: string;
  /**
   * Readable endpoint name (e.g. 'OpenRouter').
   */
  name: string;
  /**
   * API format (e.g. 'openrouter' or 'openai' for OpenAI-compatible APIs).
   */
  api_type: string;
  /**
   * Base URL for the API endpoint.
   */
  api_base?: string | null;
  /**
   * API version (optional)
   */
  api_version?: string | null;
  /**
   * if not given, all LLMs depending on this endpoint will be disabled.
   */
  api_key?: string | null;
}
/**
 * What the admin panel is allowed to see: whether a key is set, not the key.
 *
 * The panel only ever needed the boolean, and a key that reaches the browser
 * also reaches devtools, the cache and anything that logs the response.
 */
export interface LLMEndpointPublic {
  id?: string;
  created_at?: string;
  updated_at?: string;
  /**
   * Readable endpoint name (e.g. 'OpenRouter').
   */
  name: string;
  /**
   * API format (e.g. 'openrouter' or 'openai' for OpenAI-compatible APIs).
   */
  api_type: string;
  /**
   * Base URL for the API endpoint.
   */
  api_base?: string | null;
  /**
   * API version (optional)
   */
  api_version?: string | null;
  has_api_key?: boolean;
}
/**
 * LLM lab/organization metadata.
 */
export interface LLMLab {
  id?: string;
  created_at?: string;
  updated_at?: string;
  name: string;
  /**
   * An icon name from https://lobehub.com/fr/icons or a filename (e.g. 'ai2.svg') from `frontend/static/orgs/ai/`.
   */
  logo: string | null;
  /**
   * A 2 letter code from https://en.wikipedia.org/wiki/ISO_3166-1.
   */
  origin_country: string;
  logo_data?: string | null;
  logo_content_type?: string | null;
}
export interface LLMLabPublic {
  id?: string;
  created_at?: string;
  updated_at?: string;
  name: string;
  /**
   * An icon name from https://lobehub.com/fr/icons or a filename (e.g. 'ai2.svg') from `frontend/static/orgs/ai/`.
   */
  logo: string | null;
  /**
   * A 2 letter code from https://en.wikipedia.org/wiki/ISO_3166-1.
   */
  origin_country: string;
  has_custom_logo?: boolean;
  logo_version?: string | null;
}
/**
 * LLM licence metadata.
 */
export interface LLMLicense {
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
}
export interface TranslatableLegalPresentation {
  [k: string]: LegalPresentation;
}
export interface LegalPresentation {
  arena: ArenaLegalPresentation;
  sign_in: SignInLegalPresentation;
}
export interface ArenaLegalPresentation {
  title: string;
  introduction: string;
  checkbox_label: string;
  button_label?: string | null;
}
export interface SignInLegalPresentation {
  checkbox_label: string;
}
export interface LegalStatuses {
  participation: LegalStatus;
  terms: LegalStatus;
  privacy_policy: LegalStatus;
  legal_notice: LegalStatus;
  accessibility: LegalStatus;
  ecodesign: LegalStatus;
}
export interface LegalStatus {
  published: boolean;
  missing_locales: boolean;
}
/**
 * Whether a mode can draw a pair now, and what an admin should know.
 */
export interface ModeViability {
  viable: boolean;
  pool_a_size: number;
  pool_b_size: number;
  pairs: number;
  warnings?: (
    | "pool_a_empty"
    | "pool_b_empty"
    | "no_valid_pair"
    | "single_pair"
    | "unknown_llm_ids"
    | "unknown_tool_keys"
    | "tool_not_offered"
  )[];
}
/**
 * Which models a side of a mode draws from. Every field is optional and an
 * empty filter matches every enabled model. A model matches when it passes
 * every field that is set.
 */
export interface ModelFilter {
  /**
   * Leave empty to keep every model that meets the other criteria.
   */
  llm_ids?: string[];
  exclude_llm_ids?: string[];
  lab_ids?: string[];
  exclude_lab_ids?: string[];
  /**
   * Tags set on the models in the LLM form.
   */
  tags?: string[];
  exclude_tags?: string[];
  /**
   * any: at least one of the tags; all: every tag.
   */
  tags_match?: "any" | "all";
  license_ids?: string[];
  /**
   * Yes: open weights only. No: proprietary only.
   */
  public_weights?: boolean | null;
  eu_hostable?: boolean | null;
  archs?: ("moe" | "matformer" | "dense" | "maybe-moe" | "maybe-matformer" | "maybe-dense" | "na")[];
  /**
   * In billions of parameters.
   */
  size_classes?: ("XS" | "S" | "M" | "L" | "XL")[];
  /**
   * In billions.
   */
  params_min?: number | null;
  /**
   * In billions.
   */
  params_max?: number | null;
  /**
   * From A, the lowest estimated consumption, to F, the highest.
   */
  energy_classes?: ("A" | "B" | "C" | "D" | "E" | "F")[];
  /**
   * The model accepts every one of these.
   */
  inputs?: ("text" | "image" | "audio" | "video")[];
  released_after?: string | null;
  released_before?: string | null;
  /**
   * For example 90 for the last three months.
   */
  released_within_days?: number | null;
  /**
   * In US dollars per million output tokens.
   */
  price_out_max?: number | null;
  /**
   * Rate limited models are the expensive ones, with a usage cap per visitor.
   */
  rate_limited?: boolean | null;
  /**
   * Set per model in the LLM form. A system with its own retrieval or tools behind its endpoint never gets the arena's.
   */
  arena_tools?: boolean | null;
  /**
   * Only the N first models of the ranking. Models not ranked yet never match.
   */
  top_ranked?: number | null;
}
/**
 * The configuration plus how the check is faring, since a broken check
 * either refuses every message or, while the model counts as down, lets them
 * all through unchecked.
 */
export interface PromptCheckStatus {
  enabled?: boolean;
  /**
   * When the check cannot answer (timeout, OpenRouter busy, key refused), the message is refused. Off, it goes through unchecked. Either way, after several OpenRouter failures in a row, messages go through unchecked a minute at a time.
   */
  required?: boolean;
  /**
   * A decision model from OpenRouter.
   */
  model?: string;
  has_api_key: boolean;
  /**
   * The model reads it with every message. Say what is welcome here, so a health question does not look suspicious on a health arena.
   */
  description: string;
  criteria: PromptCheckCriterion[];
  /**
   * Over a sliding hour, even when the check is off. Shared by everyone behind the same IP (a school, a ministry); partner cohorts (Pix) are not counted. 0 turns the limit off, empty goes back to the instance default.
   */
  conversations_per_ip_per_hour?: number | null;
  /**
   * The same limit, for one pair of models. 0 turns it off, empty goes back to the instance default.
   */
  conversations_same_models_per_ip_per_hour?: number | null;
  updated_at: string;
  updated_by?: string | null;
  consecutive_failures?: number;
  key_rejected?: boolean;
  out_of_credits?: boolean;
  no_api_key?: boolean;
  no_model?: boolean;
  healthy?: boolean;
  warnings_shown?: number;
  default_conversations_per_ip_per_hour?: number;
  default_conversations_same_models_per_ip_per_hour?: number;
}
export interface PromptCheckCriterion {
  /**
   * Stats are counted by key: do not change it once the criterion is in use.
   */
  key: string;
  label: string;
  /**
   * A closed question about the `message`, answered yes or no.
   */
  question: string;
  yes?: string;
  no?: string;
  threshold: number;
  action: "off" | "log" | "warn" | "block";
  message?: "generic" | "self_harm" | "pii";
  [k: string]: unknown;
}
export interface PromptCheckUpsert {
  enabled?: boolean;
  /**
   * When the check cannot answer (timeout, OpenRouter busy, key refused), the message is refused. Off, it goes through unchecked. Either way, after several OpenRouter failures in a row, messages go through unchecked a minute at a time.
   */
  required?: boolean;
  /**
   * A decision model from OpenRouter.
   */
  model?: string;
  /**
   * Left empty, the check uses OPENROUTER_API_KEY.
   */
  api_key?: string | null;
  /**
   * The model reads it with every message. Say what is welcome here, so a health question does not look suspicious on a health arena.
   */
  description?: string;
  /**
   * @maxItems 32
   */
  criteria?: PromptCheckCriterion[];
  /**
   * Over a sliding hour, even when the check is off. Shared by everyone behind the same IP (a school, a ministry); partner cohorts (Pix) are not counted. 0 turns the limit off, empty goes back to the instance default.
   */
  conversations_per_ip_per_hour?: number | null;
  /**
   * The same limit, for one pair of models. 0 turns it off, empty goes back to the instance default.
   */
  conversations_same_models_per_ip_per_hour?: number | null;
}
/**
 * 'kind' is not sent: it is read off the config, so a row cannot end up
 * claiming one kind and holding the other's settings.
 */
export interface PublishDestinationUpsert {
  name: string;
  config: HuggingFaceConfigInput | S3ConfigInput;
  datasets: ("normal" | "raw")[];
  enabled?: boolean;
  publish_frequency?: "off" | "daily" | "weekly" | "monthly";
}
export interface HuggingFaceConfigInput {
  kind?: "huggingface";
  repo_path: string;
  token?: string | null;
  [k: string]: unknown;
}
export interface S3ConfigInput {
  kind?: "s3";
  endpoint: string;
  bucket: string;
  region?: string | null;
  prefix?: string;
  secure?: boolean;
  access_key?: string | null;
  secret_key?: string | null;
  [k: string]: unknown;
}
export interface PublishLegalDocumentBody {
  version: string;
  content: TranslatableAnnotatedStrFieldInfoAnnotationNoneTypeRequiredTrueMetadataMinLenMinLength1MaxLenMaxLength100000;
  effective_at?: string | null;
  confirm_publication: true;
}
export interface TranslatableAnnotatedStrFieldInfoAnnotationNoneTypeRequiredTrueMetadataMinLenMinLength1MaxLenMaxLength100000 {
  [k: string]: string;
}
export interface SelectionModeAdmin {
  id?: string;
  created_at?: string;
  updated_at?: string;
  /**
   * Lowercase letters, digits and dashes. Stored on every comparison and published with the dataset: it cannot be changed once saved.
   */
  key: string;
  /**
   * Required in the instance's main language. Shown in the arena's mode menu.
   */
  label: {
    [k: string]: string;
  };
  /**
   * Shown on the closed menu button. Leave empty to reuse the name.
   */
  short_label?: {
    [k: string]: string;
  };
  /**
   * One line under the name, to say what the visitor will get.
   */
  description?: {
    [k: string]: string;
  };
  /**
   * One of the icons the admin picker offers.
   */
  icon: string;
  /**
   * The arena needs at least one mode switched on.
   */
  enabled?: boolean;
  /**
   * Order in the mode menu, smallest first.
   */
  position?: number;
  /**
   * Preselected when a visitor arrives. Only one mode is the default: this one replaces the current one.
   */
  is_default?: boolean;
  visitor_picks?: 0 | 1 | 2;
  pool_a?: ModelFilter1;
  /**
   * Models side B is drawn from. Leave empty to draw both sides from pool A.
   */
  pool_b?: ModelFilter | null;
  pairing?: "any" | "different_lab" | "same_lab" | "different_size_class" | "same_size_class";
  sampling?: "uniform" | "fewer_votes" | "newest";
  tools_policy?: "visitor" | "none" | "forced";
  /**
   * With 'forced', the tools always on. With 'visitor', the only tools offered; leave empty to offer every tool.
   */
  tool_keys?: string[];
  /**
   * Offered only to visitors who came with one of these cohorts in the address, as in ?c=pix.
   */
  cohorts?: string[];
  /**
   * Offered only when the arena is shown in one of these languages.
   */
  locales?: ("da" | "en" | "fr" | "it" | "lt" | "nb-NO" | "sv")[];
  /**
   * Offered from this time on (UTC).
   */
  starts_at?: string | null;
  /**
   * Offered until this time (UTC).
   */
  ends_at?: string | null;
  viability: ModeViability;
}
/**
 * Models side A is drawn from.
 */
export interface ModelFilter1 {
  /**
   * Leave empty to keep every model that meets the other criteria.
   */
  llm_ids?: string[];
  exclude_llm_ids?: string[];
  lab_ids?: string[];
  exclude_lab_ids?: string[];
  /**
   * Tags set on the models in the LLM form.
   */
  tags?: string[];
  exclude_tags?: string[];
  /**
   * any: at least one of the tags; all: every tag.
   */
  tags_match?: "any" | "all";
  license_ids?: string[];
  /**
   * Yes: open weights only. No: proprietary only.
   */
  public_weights?: boolean | null;
  eu_hostable?: boolean | null;
  archs?: ("moe" | "matformer" | "dense" | "maybe-moe" | "maybe-matformer" | "maybe-dense" | "na")[];
  /**
   * In billions of parameters.
   */
  size_classes?: ("XS" | "S" | "M" | "L" | "XL")[];
  /**
   * In billions.
   */
  params_min?: number | null;
  /**
   * In billions.
   */
  params_max?: number | null;
  /**
   * From A, the lowest estimated consumption, to F, the highest.
   */
  energy_classes?: ("A" | "B" | "C" | "D" | "E" | "F")[];
  /**
   * The model accepts every one of these.
   */
  inputs?: ("text" | "image" | "audio" | "video")[];
  released_after?: string | null;
  released_before?: string | null;
  /**
   * For example 90 for the last three months.
   */
  released_within_days?: number | null;
  /**
   * In US dollars per million output tokens.
   */
  price_out_max?: number | null;
  /**
   * Rate limited models are the expensive ones, with a usage cap per visitor.
   */
  rate_limited?: boolean | null;
  /**
   * Set per model in the LLM form. A system with its own retrieval or tools behind its endpoint never gets the arena's.
   */
  arena_tools?: boolean | null;
  /**
   * Only the N first models of the ranking. Models not ranked yet never match.
   */
  top_ranked?: number | null;
}
/**
 * The whole menu order, written in one request.
 */
export interface SelectionModeOrder {
  ids: string[];
}
export interface SelectionModePreview {
  viability: ModeViability;
  pool_a: PreviewLLM[];
  pool_b: PreviewLLM[];
  sample_draws: [unknown, unknown][];
}
export interface PreviewLLM {
  id: string;
  name: string;
  lab: string;
  arena_tools: boolean;
  [k: string]: unknown;
}
/**
 * What the draw reads from a mode. A mode row has these fields too; this is
 * for rules that are not a row, like a mode being edited in the admin.
 */
export interface SelectionModeRules {
  visitor_picks?: 0 | 1 | 2;
  pool_a?: ModelFilter2;
  pool_b?: ModelFilter | null;
  pairing?: "any" | "different_lab" | "same_lab" | "different_size_class" | "same_size_class";
  sampling?: "uniform" | "fewer_votes" | "newest";
  tools_policy?: "visitor" | "none" | "forced";
  tool_keys?: string[];
}
/**
 * Which models a side of a mode draws from. Every field is optional and an
 * empty filter matches every enabled model. A model matches when it passes
 * every field that is set.
 */
export interface ModelFilter2 {
  /**
   * Leave empty to keep every model that meets the other criteria.
   */
  llm_ids?: string[];
  exclude_llm_ids?: string[];
  lab_ids?: string[];
  exclude_lab_ids?: string[];
  /**
   * Tags set on the models in the LLM form.
   */
  tags?: string[];
  exclude_tags?: string[];
  /**
   * any: at least one of the tags; all: every tag.
   */
  tags_match?: "any" | "all";
  license_ids?: string[];
  /**
   * Yes: open weights only. No: proprietary only.
   */
  public_weights?: boolean | null;
  eu_hostable?: boolean | null;
  archs?: ("moe" | "matformer" | "dense" | "maybe-moe" | "maybe-matformer" | "maybe-dense" | "na")[];
  /**
   * In billions of parameters.
   */
  size_classes?: ("XS" | "S" | "M" | "L" | "XL")[];
  /**
   * In billions.
   */
  params_min?: number | null;
  /**
   * In billions.
   */
  params_max?: number | null;
  /**
   * From A, the lowest estimated consumption, to F, the highest.
   */
  energy_classes?: ("A" | "B" | "C" | "D" | "E" | "F")[];
  /**
   * The model accepts every one of these.
   */
  inputs?: ("text" | "image" | "audio" | "video")[];
  released_after?: string | null;
  released_before?: string | null;
  /**
   * For example 90 for the last three months.
   */
  released_within_days?: number | null;
  /**
   * In US dollars per million output tokens.
   */
  price_out_max?: number | null;
  /**
   * Rate limited models are the expensive ones, with a usage cap per visitor.
   */
  rate_limited?: boolean | null;
  /**
   * Set per model in the LLM form. A system with its own retrieval or tools behind its endpoint never gets the arena's.
   */
  arena_tools?: boolean | null;
  /**
   * Only the N first models of the ranking. Models not ranked yet never match.
   */
  top_ranked?: number | null;
}
export interface SelectionModeTemplate {
  id: string;
  mode: SelectionModeDraft;
}
/**
 * A mode not saved yet, as a template fills the create form.
 */
export interface SelectionModeDraft {
  visitor_picks?: 0 | 1 | 2;
  pool_a?: ModelFilter3;
  pool_b?: ModelFilter | null;
  pairing?: "any" | "different_lab" | "same_lab" | "different_size_class" | "same_size_class";
  sampling?: "uniform" | "fewer_votes" | "newest";
  tools_policy?: "visitor" | "none" | "forced";
  tool_keys?: string[];
  key?: string;
  label?: {
    [k: string]: string;
  };
  short_label?: {
    [k: string]: string;
  };
  description?: {
    [k: string]: string;
  };
  icon?:
    | "i-ri-dice-line"
    | "i-ri-scales-3-line"
    | "i-ri-open-source-line"
    | "i-ri-map-pin-line"
    | "i-ri-ruler-line"
    | "i-ri-leaf-line"
    | "i-ri-trophy-line"
    | "i-ri-sparkling-line"
    | "i-ri-group-line"
    | "i-ri-search-line"
    | "i-ri-global-line"
    | "i-ri-government-line"
    | "i-ri-heart-pulse-line"
    | "i-ri-stethoscope-line"
    | "i-ri-graduation-cap-line"
    | "i-ri-shield-check-line"
    | "i-ri-flashlight-line";
  [k: string]: unknown;
}
/**
 * Which models a side of a mode draws from. Every field is optional and an
 * empty filter matches every enabled model. A model matches when it passes
 * every field that is set.
 */
export interface ModelFilter3 {
  /**
   * Leave empty to keep every model that meets the other criteria.
   */
  llm_ids?: string[];
  exclude_llm_ids?: string[];
  lab_ids?: string[];
  exclude_lab_ids?: string[];
  /**
   * Tags set on the models in the LLM form.
   */
  tags?: string[];
  exclude_tags?: string[];
  /**
   * any: at least one of the tags; all: every tag.
   */
  tags_match?: "any" | "all";
  license_ids?: string[];
  /**
   * Yes: open weights only. No: proprietary only.
   */
  public_weights?: boolean | null;
  eu_hostable?: boolean | null;
  archs?: ("moe" | "matformer" | "dense" | "maybe-moe" | "maybe-matformer" | "maybe-dense" | "na")[];
  /**
   * In billions of parameters.
   */
  size_classes?: ("XS" | "S" | "M" | "L" | "XL")[];
  /**
   * In billions.
   */
  params_min?: number | null;
  /**
   * In billions.
   */
  params_max?: number | null;
  /**
   * From A, the lowest estimated consumption, to F, the highest.
   */
  energy_classes?: ("A" | "B" | "C" | "D" | "E" | "F")[];
  /**
   * The model accepts every one of these.
   */
  inputs?: ("text" | "image" | "audio" | "video")[];
  released_after?: string | null;
  released_before?: string | null;
  /**
   * For example 90 for the last three months.
   */
  released_within_days?: number | null;
  /**
   * In US dollars per million output tokens.
   */
  price_out_max?: number | null;
  /**
   * Rate limited models are the expensive ones, with a usage cap per visitor.
   */
  rate_limited?: boolean | null;
  /**
   * Set per model in the LLM form. A system with its own retrieval or tools behind its endpoint never gets the arena's.
   */
  arena_tools?: boolean | null;
  /**
   * Only the N first models of the ranking. Models not ranked yet never match.
   */
  top_ranked?: number | null;
}
export interface SelectionModeUpsert {
  id?: string;
  created_at?: string;
  updated_at?: string;
  /**
   * Lowercase letters, digits and dashes. Stored on every comparison and published with the dataset: it cannot be changed once saved.
   */
  key: string;
  /**
   * Required in the instance's main language. Shown in the arena's mode menu.
   */
  label: {
    [k: string]: string;
  };
  /**
   * Shown on the closed menu button. Leave empty to reuse the name.
   */
  short_label?: {
    [k: string]: string;
  };
  /**
   * One line under the name, to say what the visitor will get.
   */
  description?: {
    [k: string]: string;
  };
  /**
   * One of the icons the admin picker offers.
   */
  icon:
    | "i-ri-dice-line"
    | "i-ri-scales-3-line"
    | "i-ri-open-source-line"
    | "i-ri-map-pin-line"
    | "i-ri-ruler-line"
    | "i-ri-leaf-line"
    | "i-ri-trophy-line"
    | "i-ri-sparkling-line"
    | "i-ri-group-line"
    | "i-ri-search-line"
    | "i-ri-global-line"
    | "i-ri-government-line"
    | "i-ri-heart-pulse-line"
    | "i-ri-stethoscope-line"
    | "i-ri-graduation-cap-line"
    | "i-ri-shield-check-line"
    | "i-ri-flashlight-line";
  /**
   * The arena needs at least one mode switched on.
   */
  enabled?: boolean;
  /**
   * Order in the mode menu, smallest first.
   */
  position?: number;
  /**
   * Preselected when a visitor arrives. Only one mode is the default: this one replaces the current one.
   */
  is_default?: boolean;
  visitor_picks?: 0 | 1 | 2;
  pool_a?: ModelFilter4;
  /**
   * Models side B is drawn from. Leave empty to draw both sides from pool A.
   */
  pool_b?: ModelFilter | null;
  pairing?: "any" | "different_lab" | "same_lab" | "different_size_class" | "same_size_class";
  sampling?: "uniform" | "fewer_votes" | "newest";
  tools_policy?: "visitor" | "none" | "forced";
  /**
   * With 'forced', the tools always on. With 'visitor', the only tools offered; leave empty to offer every tool.
   */
  tool_keys?: string[];
  /**
   * Offered only to visitors who came with one of these cohorts in the address, as in ?c=pix.
   */
  cohorts?: string[];
  /**
   * Offered only when the arena is shown in one of these languages.
   */
  locales?: ("da" | "en" | "fr" | "it" | "lt" | "nb-NO" | "sv")[];
  /**
   * Offered from this time on (UTC).
   */
  starts_at?: string | null;
  /**
   * Offered until this time (UTC).
   */
  ends_at?: string | null;
}
/**
 * Which models a side of a mode draws from. Every field is optional and an
 * empty filter matches every enabled model. A model matches when it passes
 * every field that is set.
 */
export interface ModelFilter4 {
  /**
   * Leave empty to keep every model that meets the other criteria.
   */
  llm_ids?: string[];
  exclude_llm_ids?: string[];
  lab_ids?: string[];
  exclude_lab_ids?: string[];
  /**
   * Tags set on the models in the LLM form.
   */
  tags?: string[];
  exclude_tags?: string[];
  /**
   * any: at least one of the tags; all: every tag.
   */
  tags_match?: "any" | "all";
  license_ids?: string[];
  /**
   * Yes: open weights only. No: proprietary only.
   */
  public_weights?: boolean | null;
  eu_hostable?: boolean | null;
  archs?: ("moe" | "matformer" | "dense" | "maybe-moe" | "maybe-matformer" | "maybe-dense" | "na")[];
  /**
   * In billions of parameters.
   */
  size_classes?: ("XS" | "S" | "M" | "L" | "XL")[];
  /**
   * In billions.
   */
  params_min?: number | null;
  /**
   * In billions.
   */
  params_max?: number | null;
  /**
   * From A, the lowest estimated consumption, to F, the highest.
   */
  energy_classes?: ("A" | "B" | "C" | "D" | "E" | "F")[];
  /**
   * The model accepts every one of these.
   */
  inputs?: ("text" | "image" | "audio" | "video")[];
  released_after?: string | null;
  released_before?: string | null;
  /**
   * For example 90 for the last three months.
   */
  released_within_days?: number | null;
  /**
   * In US dollars per million output tokens.
   */
  price_out_max?: number | null;
  /**
   * Rate limited models are the expensive ones, with a usage cap per visitor.
   */
  rate_limited?: boolean | null;
  /**
   * Set per model in the LLM form. A system with its own retrieval or tools behind its endpoint never gets the arena's.
   */
  arena_tools?: boolean | null;
  /**
   * Only the N first models of the ranking. Models not ranked yet never match.
   */
  top_ranked?: number | null;
}
export interface SuggestionArchiveUpdate {
  archived: boolean;
}
export interface SuggestionCategoryCreate {
  locale: "da" | "en" | "fr" | "it" | "lt" | "nb-NO" | "sv";
  title: string;
  description: string;
  icon: string;
  tooltip?: string | null;
}
export interface SuggestionCreate {
  category_id: string;
  text: string;
}
export interface SurveyOptionWrite {
  key?: string | null;
  labels: {
    [k: string]: string;
  };
  archived?: boolean;
}
export interface SurveyQuestionArchiveUpdate {
  archived: boolean;
}
export interface SurveyQuestionCreate {
  required?: boolean;
  input_type: "select" | "checkbox_group";
  labels: {
    [k: string]: string;
  };
  options: SurveyOptionWrite[];
  published?: boolean;
}
/**
 * The whole order, written in one request, as the vote tags do: one round
 * trip per drag, and the gaps archiving leaves in 'display_order' get
 * rewritten away.
 */
export interface SurveyQuestionOrder {
  ids: string[];
}
export interface SurveyQuestionUpdate {
  required: boolean;
  labels: {
    [k: string]: string;
  };
  options: SurveyOptionWrite[];
  published: boolean;
}
/**
 * What the admin panel is allowed to see: whether a credential is set,
 * never the credential.
 */
export interface ToolAdmin {
  id?: string;
  created_at?: string;
  updated_at?: string;
  /**
   * Stable identifier. For a built-in tool, the registry key (e.g. 'web_search').
   */
  key: string;
  /**
   * Name shown to visitors, in French.
   */
  label: string;
  /**
   * One line shown to visitors, in French.
   */
  description?: string | null;
  /**
   * How the tool is carried out.
   */
  kind?: "builtin" | "mcp";
  /**
   * For an MCP tool, the server address.
   */
  url?: string | null;
  /**
   * For an MCP tool, the server functions offered to models. Leave empty to offer every function the server lists.
   */
  allowed_functions?: string[] | null;
  /**
   * For web search, the only sites results may come from (e.g. 'service-public.fr'). Leave empty for the whole web.
   */
  allowed_domains?: string[] | null;
  /**
   * For web search, sites results never come from. Cannot be combined with allowed domains.
   */
  blocked_domains?: string[] | null;
  /**
   * Disabled tools are never offered to a model nor shown to a visitor.
   */
  enabled?: boolean;
  has_secret?: boolean;
}
export interface ToolUpsert {
  id?: string;
  created_at?: string;
  updated_at?: string;
  /**
   * Stable identifier. For a built-in tool, the registry key (e.g. 'web_search').
   */
  key: string;
  /**
   * Name shown to visitors, in French.
   */
  label: string;
  /**
   * One line shown to visitors, in French.
   */
  description?: string | null;
  /**
   * How the tool is carried out.
   */
  kind?: "builtin" | "mcp";
  /**
   * For an MCP tool, the server address.
   */
  url?: string | null;
  /**
   * For an MCP tool, the server functions offered to models. Leave empty to offer every function the server lists.
   */
  allowed_functions?: string[] | null;
  /**
   * For web search, the only sites results may come from (e.g. 'service-public.fr'). Leave empty for the whole web.
   */
  allowed_domains?: string[] | null;
  /**
   * For web search, sites results never come from. Cannot be combined with allowed domains.
   */
  blocked_domains?: string[] | null;
  /**
   * Disabled tools are never offered to a model nor shown to a visitor.
   */
  enabled?: boolean;
  /**
   * For a built-in tool, its provider API key. For an MCP tool, a token sent as 'Authorization: Bearer', or a whole header as 'Name: value'. Stored encrypted and never shown again.
   */
  secret?: string | null;
}
export interface UserPublic {
  id?: string;
  email: string;
  role?: "user" | "admin";
  created_at: string;
  last_seen_at: string;
  source: string;
  totp_enabled?: boolean;
}
export interface UserUpsert {
  id?: string;
  email: string;
  role?: "user" | "admin";
}
export interface VoteTagArchiveUpdate {
  archived: boolean;
}
export interface VoteTagCreate {
  sign: "positive" | "negative";
  emoji: string;
  labels: {
    [k: string]: string;
  };
}
/**
 * A whole side's order, written in one request. Sending the full list rather
 * than a step at a time lets a drag across the table cost one round trip, and
 * rewrites away the gaps deletions leave in 'display_order'.
 */
export interface VoteTagOrder {
  sign: "positive" | "negative";
  ids: string[];
}
export interface VoteTagUpdate {
  emoji: string;
  labels: {
    [k: string]: string;
  };
}
