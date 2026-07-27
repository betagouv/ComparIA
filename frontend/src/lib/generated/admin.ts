/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

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
export interface AppSettingsPatch {
  auth_access_policy?: ("anonymous_first" | "sign_in_required") | null;
  auth_domain_allowlist?: string[] | null;
  votes_objective?: number | null;
  platform_name?: string | null;
}
export interface AppSettingsPublic {
  auth_access_policy: "anonymous_first" | "sign_in_required";
  auth_domain_allowlist: string[];
  votes_objective: number;
  platform_name: string;
  has_custom_logo: boolean;
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
