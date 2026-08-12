/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export interface AdminLegalDocument {
  id: string;
  kind: "terms" | "privacy_policy";
  version: string;
  locale: string;
  content: string;
  content_hash: string;
  published_at: string;
  effective_at: string;
  retired_at: string | null;
  seeded: boolean;
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
  locale: "fr" | "da" | "sv";
  category_id: string;
  category_title: string;
  status: "available" | "archived";
  created_at: string;
  updated_at: string;
}
export interface AdminSuggestionCategory {
  id: string;
  locale: "fr" | "da" | "sv";
  key: string;
  title: string;
  description: string;
  icon: string;
  tooltip?: string | null;
  display_order: number;
  suggestion_count: number;
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
  platform_name?: string | null;
  primary_color_light?: string | null;
  primary_color_dark?: string | null;
  secondary_color_light?: string | null;
  secondary_color_dark?: string | null;
  homepage_url?: string | null;
  enabled_locales?: string[] | null;
  default_locale?: string | null;
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
  enabled_locales: string[];
  default_locale: string;
  auth_methods: string[];
  oidc_issuer: string | null;
  oidc_client_id: string | null;
  oidc_has_client_secret: boolean;
  oidc_scopes: string[];
  oidc_button_label: string | null;
  oidc_has_button_logo: boolean;
  oidc_button_logo_content_type: string | null;
  updated_at: string;
  updated_by?: string | null;
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
  logo: string;
  /**
   * A 2 letter code from https://en.wikipedia.org/wiki/ISO_3166-1.
   */
  origin_country: string;
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
export interface PromptCheckPatch {
  enabled?: boolean | null;
  model?: string | null;
  api_key?: string | null;
  categories?: {
    [k: string]: {
      [k: string]: unknown;
    };
  } | null;
}
/**
 * The configuration plus how the check is faring. It fails open, so one
 * that has stopped working looks exactly like one that finds nothing.
 */
export interface PromptCheckStatus {
  enabled: boolean;
  model: string;
  has_api_key: boolean;
  categories: {
    [k: string]: {
      [k: string]: unknown;
    };
  };
  updated_at: string;
  updated_by?: string | null;
  consecutive_failures?: number;
  healthy?: boolean;
  warnings_shown?: number;
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
  locale: string;
  content: string;
  effective_at?: string | null;
  confirm_publication: true;
}
export interface SuggestionArchiveUpdate {
  archived: boolean;
}
export interface SuggestionCategoryCreate {
  locale: "fr" | "da" | "sv";
  title: string;
  description: string;
  icon: string;
  tooltip?: string | null;
}
export interface SuggestionCreate {
  category_id: string;
  text: string;
}
export interface UpdateLegalPresentationBody {
  presentation: LegalPresentation;
}
export interface LegalPresentation {
  arena: ArenaLegalPresentation;
  sign_in: SignInLegalPresentation;
  [k: string]: unknown;
}
export interface ArenaLegalPresentation {
  title: string;
  introduction: string;
  checkbox_label: string;
  button_label?: string | null;
  [k: string]: unknown;
}
export interface SignInLegalPresentation {
  checkbox_label: string;
  [k: string]: unknown;
}
export interface UserPublic {
  id?: string;
  email: string;
  role?: "user" | "admin";
  created_at: string;
  last_seen_at: string;
  source: string;
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
