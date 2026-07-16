/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export interface AppSettingsPatch {
  auth_access_policy?: ("anonymous_first" | "sign_in_required") | null;
  auth_domain_allowlist?: string[] | null;
  votes_objective?: number | null;
  platform_name?: string | null;
  terms_content?: string | null;
}
export interface AppSettingsPublic {
  auth_access_policy: "anonymous_first" | "sign_in_required";
  auth_domain_allowlist: string[];
  votes_objective: number;
  platform_name: string;
  has_custom_logo: boolean;
  terms_content: string | null;
  updated_at: string;
  updated_by?: string | null;
}
/**
 * LLM definition.
 *
 * Contains basic LLM information and links to licence, lab and endpoint.
 *
 * Attributes
 * ----------
 * human_id
 *     Readable id (legacy id), usually the id specified in `api_model_id`
 *     `'{labid}/{llmid}'`.
 * api_model_id
 *     Identifier used in API calls.
 * status
 *     Current status:
 *       - 'enabled': callable and displayed in llm list + rankings;
 *       - 'archived': not callable but displayed in llm list + rankings,
 *       - 'disabled': not callable and hidden in llm list + rankings.
 * name
 *     Readable name.
 * rate_limited
 *     Apply rate limits (usually for high API costs LLMs).
 * release_date
 *     Release date.
 * knowledge_cutoff
 *     Date after which the LLM no longer has knowledge.
 * arch
 *     LLM architecture, Use `maybe-*` if information is not confirmed.
 * params
 *     Total parameters in billions.
 * active_params
 *     Active parameters in billions (only for MoE LLMs).
 * context_tokens
 *     Size of its context window in tokens.
 * quantization
 *     Quantization scheme applied (q4, q8, or None for full precision).
 * inputs
 *     What kind of media the LLM can have in input.
 * public_weights
 *     Whether the LLM weights are public.
 * public_training_data
 *     Whether the LLM training data is public.
 * public_training_code
 *     Whether the LLM training code is public.
 * eu_hostable
 *     Whether the LLM is hostable in the EU.
 * price_in
 *     Price per million input tokens in €.
 * price_out
 *     Price per million output tokens in €.
 * system_prompt
 *     System message to add in llm call if specified
 * links
 *     List of links to display in LLM card.
 */
export interface LLMData {
  id?: string;
  created_at?: string;
  updated_at?: string;
  lab_id: string;
  license_id: string;
  endpoint_id: string | null;
  human_id: string;
  api_model_id: string | null;
  status: "archived" | "disabled" | "enabled";
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
}
export interface Link {
  text: string;
  url: string;
  [k: string]: unknown;
}
/**
 * LLM endpoint configuration for API calls.
 *
 * Attributes
 * ----------
 * name
 *     Readable endpoint name (e.g. 'OpenRouter').
 * api_type
 *     API format (e.g. 'openrouter' or 'openai' for OpenAI-compatible APIs).
 * api_base
 *     Base URL for the API endpoint.
 * api_version
 *     API version (optional)
 * api_key
 *     API secret key.
 */
export interface LLMEndpoint {
  id?: string;
  created_at?: string;
  updated_at?: string;
  name: string;
  api_type: string;
  api_base?: string | null;
  api_version?: string | null;
  api_key?: string | null;
}
/**
 * LLM lab/organization metadata.
 *
 * Attributes
 * ----------
 * name
 *     Lab name.
 * logo
 *     An icon name from https://lobehub.com/fr/icons or a filename
 *     (e.g. 'ai2.svg') from `frontend/static/orgs/ai/`.
 * origin_country
 *     Lab's origin country as a 2 letter code from https://en.wikipedia.org/wiki/ISO_3166-1.
 */
export interface LLMLab {
  id?: string;
  created_at?: string;
  updated_at?: string;
  name: string;
  logo: string;
  origin_country: string;
}
/**
 * LLM licence metadata.
 *
 * Attributes
 * ----------
 * kind
 *     Licence type.
 * name
 *     Licence name (e.g. 'Apache 2.0' or 'MIT').
 * reuse
 *     Whether the licence allows reuse/redistribution.
 * commercial_use
 *     Whether the licence allows commercial use.
 */
export interface LLMLicense {
  id?: string;
  created_at?: string;
  updated_at?: string;
  kind: "proprietary" | "open-weights" | "open-source";
  name: string;
  reuse: boolean;
  commercial_use: boolean;
}
export interface UserPublic {
  id: string;
  email: string;
  role: string;
  created_at: string;
  last_seen_at: string;
  source: string;
}
