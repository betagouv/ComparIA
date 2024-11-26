<script context="module" lang="ts">
export interface ExtendedLikeData {
		index: number | [number, number];
		value: any;
		liked?: boolean;
		prefs?: string[];
		comment?: boolean;
	}
</script>
<script lang="ts">
	import {
		format_chat_for_sharing,
		type UndoRetryData,
		is_one_of_last_two_bot_msgs,
		group_messages,
		load_components,
		get_components_from_messages,
	} from "./utils";
	import type { NormalisedMessage } from "../types";
	import { copy } from "@gradio/utils";
	import Message from "./Message.svelte";

	import { dequal } from "dequal/lite";
	import {
		afterUpdate,
		createEventDispatcher,
		type SvelteComponent,
		type ComponentType,
		tick,
		onMount,
	} from "svelte";

	import { Trash, Community, ScrollDownArrow } from "@gradio/icons";
	import IconButton from "./IconButton.svelte";
	import type { SelectData, LikeData } from "@gradio/utils";
	import type { ExampleMessage } from "../types";
	import { MarkdownCode as Markdown } from "@gradio/markdown-code";
	import type { FileData, Client } from "@gradio/client";
	// import type { I18nFormatter } from "js/core/src/gradio_helper";
	import Pending from "./Pending.svelte";
	import { ShareError } from "@gradio/utils";
	import { Gradio } from "@gradio/utils";

	export let value: NormalisedMessage[] | null = [];
	let old_value: NormalisedMessage[] | null = null;

	import CopyAll from "./CopyAll.svelte";

	export let _fetch: typeof fetch;
	export let load_component: Gradio["load_component"];

	let _components: Record<string, ComponentType<SvelteComponent>> = {};

	const is_browser = typeof window !== "undefined";

	async function update_components(): Promise<void> {
		_components = await load_components(
			get_components_from_messages(value),
			_components,
			load_component,
		);
	}

	$: value, update_components();

	export let latex_delimiters: {
		left: string;
		right: string;
		display: boolean;
	}[];
	export let disabled = false;
	export let pending_message = false;
	export let generating = false;
	export let selectable = false;
	export let likeable = false;
	export let show_share_button = false;
	export let show_copy_all_button = false;
	export let rtl = false;
	export let show_copy_button = false;
	export let sanitize_html = true;
	export let render_markdown = true;
	export let line_breaks = true;
	export let autoscroll = true;
	export let theme_mode: "system" | "light" | "dark";
	// export let i18n: I18nFormatter;
	export let layout: "bubble" | "panel" = "bubble";
	export let placeholder: string | null = null;
	export let upload: Client["upload"];
	export let _retryable = false;
	export let _undoable = false;
	export let like_user_message = false;
	export let root: string;

	export const negative_prefs = [
		"incorrect",
		"superficial",
		"instructions-not-followed",
	];

	export const positive_prefs = [
		"useful",
		"complete",
		"creative",
		"clear-formatting",
	];

	let target: HTMLElement | null = null;

	onMount(() => {
		target = document.querySelector("div.gradio-container");
	});

	let div: HTMLDivElement;

	let show_scroll_button = false;
	
	const dispatch = createEventDispatcher<{
		change: undefined;
		select: SelectData;
		like: ExtendedLikeData;
		undo: UndoRetryData;
		retry: UndoRetryData;
		share: any;
		error: string;
		example_select: SelectData;
	}>();

	function is_at_bottom(): boolean {
		return div && div.offsetHeight + div.scrollTop > div.scrollHeight - 100;
	}

	function scroll_to_bottom(): void {
		if (!div) return;
		div.scrollTo(0, div.scrollHeight);
		show_scroll_button = false;
	}

	let scroll_after_component_load = false;
	function on_child_component_load(): void {
		if (scroll_after_component_load) {
			scroll_to_bottom();
			scroll_after_component_load = false;
		}
	}

	async function scroll_on_value_update(): Promise<void> {
		if (!autoscroll) return;

		if (is_at_bottom()) {
			// Child components may be loaded asynchronously,
			// so trigger the scroll again after they load.
			scroll_after_component_load = true;

			await tick(); // Wait for the DOM to update so that the scrollHeight is correct
			scroll_to_bottom();
		} else {
			show_scroll_button = true;
		}
	}
	onMount(() => {
		scroll_on_value_update();
	});
	$: if (value || pending_message || _components) {
		scroll_on_value_update();
	}

	onMount(() => {
		function handle_scroll(): void {
			if (is_at_bottom()) {
				show_scroll_button = false;
			} else {
				scroll_after_component_load = false;
			}
		}

		div?.addEventListener("scroll", handle_scroll);
		return () => {
			div?.removeEventListener("scroll", handle_scroll);
		};
	});

	// afterUpdate(() => {
	// });

	$: {
		if (!dequal(value, old_value)) {
			old_value = value;
			dispatch("change");
		}
	}

	$: groupedMessages = value && group_messages(value, "messages");

	function handle_like(
		i: number,
		j: number,
		message: NormalisedMessage,
		selected: string[] | string | null,
	): void {
		if (!groupedMessages) return;
		
		var user_msg_offset = Math.floor(i / 2);
		var chatbot_index = i + j + user_msg_offset;

		const msg = groupedMessages[i][j];

		console.log(selected);
		if (selected === "like") {
			value[chatbot_index].liked = true;
			value[chatbot_index].disliked = false;
			if (value[chatbot_index].prefs) {
				value[chatbot_index].prefs = value[chatbot_index].prefs.filter(
					(item) => !negative_prefs.includes(item),
				);
			}

			dispatch("like", {
				index: msg.index,
				value: msg.content,
				liked: true,
				prefs: value[chatbot_index].prefs,
			});
		} else if (selected === "dislike") {
			value[chatbot_index].liked = false;
			value[chatbot_index].disliked = true;
			if (value[chatbot_index].prefs) {
				value[chatbot_index].prefs = value[chatbot_index].prefs.filter(
					(item) => !positive_prefs.includes(item),
				);
			}
			dispatch("like", {
				index: msg.index,
				value: msg.content,
				liked: false,
				prefs: value[chatbot_index].prefs,
			});
		} else if (selected === "none") {
			value[chatbot_index].liked = false;
			value[chatbot_index].disliked = false;
			value[chatbot_index].prefs = [];
			dispatch("like", {
				index: msg.index,
				value: msg.content,
				liked: null,
				prefs: [],
			});
		}

		if (Array.isArray(selected)) {
			value[chatbot_index].prefs = selected;
			// console.log("msg")
			// console.log(msg)
			// console.log("message")
			// console.log(message)
			dispatch("like", {
				index: msg.index,
				value: msg.content,
				liked: msg.liked,
				prefs: selected,
			});
		}
	}
</script>

{#if value !== null && value.length > 0}
	<div>
		{#if show_share_button}
			<IconButton
				Icon={Community}
				on:click={async () => {
					try {
						// @ts-ignore
						const formatted = await format_chat_for_sharing(value);
						dispatch("share", {
							description: formatted,
						});
					} catch (e) {
						console.error(e);
						let message =
							e instanceof ShareError
								? e.message
								: "Share failed.";
						dispatch("error", message);
					}
				}}
			>
				<Community />
			</IconButton>
		{/if}
		{#if show_copy_all_button}
			<CopyAll {value} />
		{/if}
	</div>
{/if}

<div
	class={layout === "bubble" ? "bubble-wrap" : "panel-wrap"}
	bind:this={div}
	role="log"
	aria-label="chatbot conversation"
	aria-live="polite"
>
	{#if value !== null && value.length > 0 && groupedMessages !== null}
		<div class="message-wrap" use:copy>
			{#each groupedMessages as messages, i}
				{@const role = messages[0].role === "user" ? "user" : "bot"}
				<div class="message-row {layout} {role}-row">
					{#each messages as message, j}
						<Message
							messages={[message]}
							{role}
							{layout}
							{dispatch}
							{_fetch}
							{line_breaks}
							{theme_mode}
							{target}
							{root}
							{upload}
							{selectable}
							{sanitize_html}
							{render_markdown}
							{rtl}
							{i}
							{value}
							{latex_delimiters}
							{_components}
							{disabled}
							generating={generating &&
								is_one_of_last_two_bot_msgs([message], value)}
							show_like={role === "user"
								? likeable && like_user_message
								: likeable}
							show_retry={_retryable &&
								is_one_of_last_two_bot_msgs([message], value)}
							show_undo={_undoable &&
								is_one_of_last_two_bot_msgs([message], value)}
							show_copy_button={role === "user"
								? false
								: show_copy_button}
							handle_action={(selected) =>
								handle_like(i, j, message, selected)}
							scroll={is_browser ? scroll : () => {}}
							liked={message.liked}
							disliked={message.disliked}
							comment={message.comment}

						/>
					{/each}
				</div>

				{#if role === "user" && i === 0}
					<div class="prose text-center fr-mb-4w fr-mb-md-0">
						<span class="step-badge">Étape 1/2</span>
						<h4 class="fr-mt-2w fr-mb-1v">
							Que pensez-vous des réponses ?
						</h4>
						<p class="text-grey fr-text--sm">
							Prêtez attention au fond et à la forme puis évaluez
							chaque réponse
						</p>
					</div>
				{/if}
			{/each}
			{#if pending_message}
				<Pending {layout} />
			{/if}
		</div>
	{:else}
		<div class="placeholder-content">
			{#if placeholder !== null}
				<div class="placeholder">
					<Markdown message={placeholder} {latex_delimiters} {root} />
				</div>
			{/if}
		</div>
	{/if}
</div>

{#if show_scroll_button}
	<div class="scroll-down-button-container">
		<IconButton
			Icon={ScrollDownArrow}
			label="Scroll down"
			size="large"
			on:click={scroll_to_bottom}
		/>
	</div>
{/if}

<style>
	.placeholder-content {
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.placeholder {
		align-items: center;
		display: flex;
		justify-content: center;
		height: 100%;
		flex-grow: 1;
	}

	.panel-wrap {
		width: 100%;
		/* overflow-y: auto; */
		background-color: #fcfcfd;
	}

	.bubble-wrap {
		width: 100%;
		/* overflow-y: auto; */
		height: 100%;
		padding-top: var(--spacing-xxl);
	}

	.step-badge {
		border-radius: 3.75em;
		text-align: center;
		background-color: #ececfe;
		padding: 5px 10px;
		font-weight: bold;
	}

	@media (prefers-color-scheme: dark) {
		.bubble-wrap {
			background: var(--background-fill-secondary);
		}
	}

	.message-wrap {
		padding: 2em;
	}

	/* .message-wrap {
		display: flex;
		flex-direction: column;
		justify-content: space-between;
		margin-bottom: var(--spacing-xxl);
	} */

	/* .message-wrap :global(.prose.chatbot.md) {
		opacity: 0.8;
		overflow-wrap: break-word;
	} */

	/* .message-wrap :global(.message-row .md img) {
		border-radius: var(--radius-xl);
		margin: var(--size-2);
		width: 400px;
		max-width: 30vw;
		max-height: 30vw;
	} */

	/* link styles */
	.message-wrap :global(.message a) {
		color: var(--color-text-link);
		text-decoration: underline;
	}

	/* table styles */
	.message-wrap :global(.bot table),
	.message-wrap :global(.bot tr),
	.message-wrap :global(.bot td),
	.message-wrap :global(.bot th) {
		border: 1px solid var(--border-color-primary);
	}

	.message-wrap :global(.user table),
	.message-wrap :global(.user tr),
	.message-wrap :global(.user td),
	.message-wrap :global(.user th) {
		border: 1px solid var(--border-color-accent);
	}

	/* KaTeX */
	/* .message-wrap :global(span.katex) {
		font-size: var(--text-lg);
		direction: ltr;
	}

	.message-wrap :global(span.katex-display) {
		margin-top: 0;
	} */

	/* .message-wrap :global(pre) {
		position: relative;
	}

	.message-wrap :global(.grid-wrap) {
		max-height: 80% !important;
		max-width: 600px;
		object-fit: contain;
	}

	.message-wrap > div :global(p:not(:first-child)) {
		margin-top: var(--spacing-xxl);
	}

	.message-wrap {
		display: flex;
		flex-direction: column;
		justify-content: space-between;
		margin-bottom: var(--spacing-xxl);
	} */

	/* .panel-wrap :global(.message-row:first-child) {
		padding-top: calc(var(--spacing-xxl) * 2);
	} */

	.message-row {
		justify-content: flex-end;
		width: 100%;
	}

	.user-row {
		display: flex;
		justify-content: flex-end;
		width: 100%;
		padding: 2em;
	}
	.bot-row {
		display: grid;
		gap: 2em;
		grid-template-columns: 1fr;
		/* align-self: flex-start; */

		/* grid-template-columns: repeat(2, 1fr); */
	}
	@media (min-width: 48em) {
		.bot-row {
			padding: 2em;
			grid-template-columns: 1fr 1fr;
			grid-auto-rows: 1fr;
		}
	}

	.scroll-down-button-container {
		position: absolute;
		bottom: 10px;
		left: 50%;
		transform: translateX(-50%);
		z-index: var(--layer-top);
	}
	.scroll-down-button-container :global(button) {
		border-radius: 50%;
		box-shadow: var(--shadow-drop);
		transition:
			box-shadow 0.2s ease-in-out,
			transform 0.2s ease-in-out;
	}
	.scroll-down-button-container :global(button:hover) {
		box-shadow:
			var(--shadow-drop),
			0 2px 2px rgba(0, 0, 0, 0.05);
		transform: translateY(-2px);
	}
</style>
