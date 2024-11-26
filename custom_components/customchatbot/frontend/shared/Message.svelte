<script lang="ts">
	import { is_component_message } from "../shared/utils";
	import type { Client } from "@gradio/client";
	import type { NormalisedMessage } from "../types";
	import { MarkdownCode as Markdown } from "@gradio/markdown-code";
	// import type { I18nFormatter } from "js/core/src/gradio_helper";
	import type { ComponentType, SvelteComponent } from "svelte";
	import ButtonPanel from "./ButtonPanel.svelte";
	import LikePanel from "./LikePanel.svelte";
	import DislikePanel from "./DislikePanel.svelte";

	import Pending from "./Pending.svelte";

	export let value: NormalisedMessage[];
	export let dislikeValue: (string | number)[] = [];
	export let likeValue: (string | number)[] = [];

	export let role = "user";
	export let messages: NormalisedMessage[] = [];
	export let layout: "bubble" | "panel";
	// export let bubble_full_width: boolean;
	export let render_markdown: boolean;
	export let latex_delimiters: {
		left: string;
		right: string;
		display: boolean;
	}[];
	export let sanitize_html: boolean;
	export let selectable: boolean;
	export let _fetch: typeof fetch;
	export let rtl: boolean;
	export let dispatch: any;
	// export let i18n: I18nFormatter;
	export let line_breaks: boolean;
	export let upload: Client["upload"];
	export let target: HTMLElement | null;
	export let root: string;
	export let disabled = false;

	export let theme_mode: "light" | "dark" | "system";
	export let _components: Record<string, ComponentType<SvelteComponent>>;
	export let i: number;
	export let show_copy_button: boolean;
	export let generating: boolean;
	export let show_like: boolean;
	export let show_retry: boolean;
	export let show_undo: boolean;
	export let liked: boolean = false;
	export let disliked: boolean = false;
	export let prefs: string[] = [];
	export let comment: string | undefined;

	export let handle_action: (selected: string | null, value?: string[]) => void;
	export let scroll: () => void;

	function get_message_label_data(message: NormalisedMessage): string {
		if (message.type === "text") {
			return message.content;
		} else if (
			message.type === "component" &&
			message.content.component === "file"
		) {
			if (Array.isArray(message.content.value)) {
				return `file of extension type: ${message.content.value[0].orig_name?.split(".").pop()}`;
			}
			return (
				`file of extension type: ${message.content.value?.orig_name?.split(".").pop()}` +
				(message.content.value?.orig_name ?? "")
			);
		}
		return `a component of type ${message.content.component ?? "unknown"}`;
	}

	function get_message_bot_position(message: NormalisedMessage): string {
		if (message.role === "assistant") {
			return message.metadata.bot === "a" ? "left" : "right";
		} else {
			return "";
		}
	}

	type ButtonPanelProps = {
		disabled: boolean;
		show: boolean;
		handle_action: (selected: string | null) => void;
		likeable: boolean;
		show_retry: boolean;
		show_undo: boolean;
		generating: boolean;
		show_copy_button: boolean;
		message: NormalisedMessage[] | NormalisedMessage;
		position: "left" | "right";
		layout: "bubble" | "panel";
	};

	let button_panel_props: ButtonPanelProps;
	$: button_panel_props = {
		show: show_like || show_retry || show_undo || show_copy_button,
		handle_action,
		likeable: show_like,
		show_retry,
		show_undo,
		disabled,
		generating,
		show_copy_button,
		message: messages,
		position: role === "user" ? "right" : "left",
		layout,
	};

	// type PrefsPanelProps = {
	// 	message: typeof messages;
	// 	show: boolean;
	// 	value: (string | number)[];
	// 	choices: [string, string | number][];
	// 	handle_action: (selected: string | null) => void;
	// };
</script>

<!-- {#if role === "user"} -->

{#each messages as message, thought_index}
	<div
		class="message {role} {get_message_bot_position(message)}"
		class:message-markdown-disabled={!render_markdown}
		class:thought={thought_index > 0}
	>
		<button
			data-testid={role}
			class:latest={i === value.length - 1}
			class:message-markdown-disabled={!render_markdown}
			style:user-select="text"
			class:selectable
			style:cursor={selectable ? "default" : "default"}
			style:text-align={rtl ? "right" : "left"}
			dir={rtl ? "rtl" : "ltr"}
			aria-label={role + "'s message: " + get_message_label_data(message)}
		>
			{#if message.type === "text"}
				<div>
					{#if message.role === "assistant"}
						<div class="model-title">
							{#if message.metadata?.bot === "a"}
								<svg class="inline" width="26" height="32"
									><circle
										cx="13"
										cy="13"
										r="12"
										fill="#A96AFE"
										stroke="none"
									></circle></svg
								>
								<h3 class="inline">Modèle A</h3>
							{:else if message.metadata?.bot === "b"}
								<svg class="inline" width="26" height="32"
									><circle
										cx="13"
										cy="13"
										r="12"
										fill="#ff9575"
										stroke="none"
									></circle></svg
								>
								<h3 class="inline">Modèle B</h3>
							{/if}
						</div>
						<Markdown
							message={message.content}
							{latex_delimiters}
							{sanitize_html}
							{render_markdown}
							{line_breaks}
							on:load={scroll}
							{root}
						/>
						{#if generating}
							<Pending />
							<!-- <br /><br /><em>En attente de la réponse…</em> -->
						{/if}
					{:else}
						<Markdown
							message={message.content}
							{latex_delimiters}
							{sanitize_html}
							{render_markdown}
							{line_breaks}
							on:load={scroll}
							{root}
						/>
					{/if}
				</div>
			{/if}
			{#if message.role === "assistant"}
				<ButtonPanel {...button_panel_props} />
			{/if}
		</button>
		{#if message.disliked}
			<DislikePanel
				show={disliked}
				value={dislikeValue}
				{handle_action}
			/>
		{/if}
		{#if message.liked}
			<LikePanel
				show={liked}
				value={likeValue}
				{handle_action}
			/>
		{/if}
	</div>
{/each}

<style>
	.model-title {
		margin-bottom: 0.5em;
	}

	.message {
		position: relative;
		/* width: 100%; */
	}

	.prose {
		color: var(--text-default-grey);
	}

	.component {
		padding: 0;
		border-radius: var(--radius-md);
		width: fit-content;
		overflow: hidden;
	}
	/* .message-wrap,
	.message-row,
	.flex-wrap,
	.styler {
		background-color: #fcfcfd;
	} */

	.message.bot button {
		border-color: #e5e5e5;
		border-width: 1px;
		border-style: solid;
		/* border-radius: 0.5rem; */
		border-radius: 0.5rem;
		background-color: white;
		display: grid;
	}
	/* @media (min-width: 48em) {
		.message.bot button {
			height: 100%;
		}
	} */

	/* .message-row :global(img) {
		margin: var(--size-2);
		max-height: 300px;
	} */

	.message-markdown-disabled {
		white-space: pre-line;
	}

	@media (min-width: 48em) {
		.user {
			width: 60% !important;
		}
	}
	.user {
		width: 100%;
		margin-left: auto;
		background-color: var(--grey-950-100);
		--hover-tint: var(--grey-950-100);
		border-radius: 0.75rem;

		/* border-width: 1px;
		border-radius: var(--radius-md);
		align-self: flex-start;
		border-bottom-right-radius: 0;
		box-shadow: var(--shadow-drop);
		align-self: flex-start;
		text-align: right;
		padding: var(--spacing-sm) var(--spacing-xl);
		border-color: var(--border-color-accent-subdued);
		background-color: var(--color-accent-soft); */
	}

	.bot button,
	.bot button:hover,
	.bot button:active {
		background-color: white;
		--hover-tint: white;
		--active-tint: white;

		color: var(--text-default-grey);
	}

	.user button,
	.user button:hover,
	.user button:active {
		background-color: transparent;
		--hover-tint: transparent;
		--active-tint: transparent;

		color: var(--text-default-grey);
	}

	/* message content */
	/* {
		display: flex;
		flex-direction: column;
		width: calc(100% - var(--spacing-xxl));
		max-width: 100%;
		color: var(--body-text-color);
		font-size: var(--chatbot-text-size);
		overflow-wrap: break-word;
		width: 100%;
		height: 100%;
		border: none !important;
		box-shadow: none !important;
		display: flex;
		flex-direction: column;
		max-width: 100%;
		color: var(--body-text-color);
		font-size: var(--chatbot-text-size);
		overflow-wrap: break-word;
	} */

	/* .user {
		border-width: 1px;
		border-radius: var(--radius-md);
		align-self: flex-start;
		border-bottom-right-radius: 0;
		box-shadow: var(--shadow-drop);
		text-align: right;
		padding: var(--spacing-sm) var(--spacing-xl);
		border-color: var(--border-color-accent-subdued);
		background-color: var(--color-accent-soft);
	} */
	.selectable {
		cursor: default;
	}

	@keyframes dot-flashing {
		0% {
			opacity: 0.8;
		}
		50% {
			opacity: 0.5;
		}
		100% {
			opacity: 0.8;
		}
	}

	.message > button {
		width: 100%;
		padding: 1.25rem;
		padding-right: 1.75rem;
	}
	.html {
		padding: 0;
		border: none;
		background: none;
	}

	/* .panel .bot,
	.panel .user {
		border: none;
		box-shadow: none;
		background-color: var(--background-fill-secondary);
	} */

	/* .panel.user-row {
		background-color: var(--color-accent-soft);
	} */

	/* .panel .user-row,
	.panel .bot-row {
		align-self: flex-start;
	}

	.panel .user :global(*),
	.panel .bot :global(*) {
		text-align: left;
	}

	.panel .user {
		background-color: var(--color-accent-soft);
	}

	.panel .user-row {
		background-color: var(--color-accent-soft);
		align-self: flex-start;
	}

	.panel .message {
		margin-bottom: var(--spacing-md);
	} */

	h1,
	h2,
	h3,
	h4,
	h5,
	h6 {
		font-weight: 700;
		font-size: 1.25rem !important;
	}

	/* @media (min-width: 48em) {

	} */

	p {
		text-align: left !important;
		color: var(--text-active-grey);
	}

	ol,
	ul {
		font-size: initial !important;
		color: var(--text-active-grey);
	}
</style>
