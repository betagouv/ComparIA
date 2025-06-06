<script context="module" lang="ts">
	// import warningicon from "./shared/fr-warning-fill.svg";

	export interface ExtendedLikeData {
		index: number | [number, number];
		value: any;
		liked?: boolean;
		prefs?: string[];
		comment?: string;
	}
</script>

<script lang="ts">
	import {
		type UndoRetryData,
		is_one_of_last_two_bot_msgs,
		group_messages,
	} from "./utils";
	import type { NormalisedMessage } from "../types";
	import { copy } from "@gradio/utils";
	import Message from "./Message.svelte";

	import { dequal } from "dequal/lite";
	import { afterUpdate, createEventDispatcher, tick, onMount } from "svelte";

	import { Trash, Community, ScrollDownArrow } from "@gradio/icons";
	import IconButton from "./IconButton.svelte";
	import type { SelectData, LikeData } from "@gradio/utils";
	import type { ExampleMessage } from "../types";
	import { MarkdownCode as Markdown } from "@gradio/markdown-code";
	import type { FileData, Client } from "@gradio/client";
	// import type { I18nFormatter } from "js/core/src/gradio_helper";
	import Pending from "./Pending.svelte";
	// import { Retry } from "@gradio/icons";

	export let value: NormalisedMessage[] | null = [];
	let old_value: NormalisedMessage[] | null = null;

	import CopyAll from "./CopyAll.svelte";

	export let _fetch: typeof fetch;

	const is_browser = typeof window !== "undefined";

	$: value;

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
	// export let upload: Client["upload"];
	export let _retryable = false;
	export let _undoable = false;
	export let like_user_message = false;
	export let root: string;

	import LikePanel from "./LikePanel.svelte";

	import ThumbUpActive from "./ThumbUpActive.svelte";
	import ThumbDownActive from "./ThumbDownActive.svelte";

	export let likeValue: string[] = [];
	export const positive_choices: [string, string][] = [
		["Utile", "useful"],
		["Complète", "complete"],
		["Créative", "creative"],
		["Mise en forme claire", "clear-formatting"],
	];
	export let dislikeValue: string[] = [];
	export const negative_choices: [string, string][] = [
		["Incorrecte", "incorrect"],
		["Superficielle", "superficial"],
		["Instructions non suivies", "instructions-not-followed"],
	];

	export const positive_prefs = positive_choices.map((choice) => choice[1]);
	export const negative_prefs = negative_choices.map((choice) => choice[1]);

	let target: HTMLElement | null = null;

	onMount(() => {
		target = document.querySelector("div.gradio-container");
	});

	let div: HTMLDivElement;

	let show_scroll_button = false;

	export let commenting: number | undefined = undefined;

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
	$: if (value || pending_message) {
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

	export let hasError: boolean = false;
	export let errorString: string = null;
	$: {
		errorString = null;

		for (const messages of groupedMessages) {
			for (const message of messages) {
				if (message?.error) {
					errorString = message.error;
					break;
				}
			}
			if (errorString !== null) {
				break;
			}
		}

		hasError = errorString !== null;
	}

	$: {
		if (!dequal(value, old_value)) {
			old_value = value;
			dispatch("change");
		}
	}
	$: groupedMessages = value && group_messages(value);

	var comment: string = "";
	var commenting_model: "A" | "B" | "" = "";
	$: {
		if (commenting != undefined) {
			value[commenting].comment = comment;
		}
	}

	function sendComment(chatbot_index) {
		// console.log(value[chatbot_index].comment);
		// console.log(comment);
		value[chatbot_index].commented = value[chatbot_index].comment != "";
		dispatch("like", {
			index: chatbot_index,
			value: "",
			comment: value[chatbot_index].comment,
		});
		// commenting = undefined;
		// comment = "";
	}
	function handle_retry_last(): void {
		// svelte custom_components/customchatbot/frontend/shared/ChatBot.svelte (237-238)
		const lastGroup = groupedMessages[groupedMessages.length - 1];
		const lastMessage =
			lastGroup && lastGroup.length > 0
				? lastGroup[lastGroup.length - 1]
				: null;
		console.log("RETRYING");

		dispatch("retry", {
			index: lastMessage.index,
			value: lastMessage.error,
			// lastMessage.metadata?.error ||
			//  ||
			// lastMessage.content,
			// value: msg.content,
			// error: msg.metadata?.error || msg.error
		});
	}
	// TODO: rename or split this function
	function handle_action(
		i: number,
		j: number,
		message: NormalisedMessage,
		selected: string[] | string | null,
	): void {
		if (!groupedMessages) return;

		var user_msg_offset = Math.floor(i / 2);
		var chatbot_index = i + j + user_msg_offset;

		const msg = groupedMessages[i][j];
		if (selected === "retry") {
			console.log("RETRYING");

			dispatch("retry", {
				index: msg.index,
				value: msg.error,
				// value: msg.error || msg.content,
				// value: msg.content,
				// error: msg.metadata?.error || msg.error
			});
		}
		if (selected === "commenting") {
			commenting = chatbot_index;
			if (value[chatbot_index].comment === undefined) {
				value[chatbot_index].comment = "";
				comment = "";

				value[chatbot_index].commented = true;
			} else {
				comment = value[chatbot_index].comment;
				value[chatbot_index].commented = true;
			}
			commenting_model = j === 0 ? "A" : "B";
		}

		// console.log(selected);
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
					(item) => !positive_choices[1].includes(item),
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
			{#if pending_message}
			<Pending />
			{/if}
			{#each groupedMessages as messages, i}
				{@const role = messages[0].role === "user" ? "user" : "bot"}
				<div class="message-row {layout} {role}-row">
					{#each messages as message, j}
						<Message
							{message}
							{role}
							{layout}
							{dispatch}
							{_fetch}
							{line_breaks}
							{theme_mode}
							{target}
							{root}
							{selectable}
							{sanitize_html}
							{render_markdown}
							{rtl}
							{i}
							{value}
							{latex_delimiters}
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
								handle_action(i, j, message, selected)}
							scroll={is_browser ? scroll : () => {}}
							liked={message.liked}
							disliked={message.disliked}
							comment={message.comment}
						/>
					{/each}

					{#each messages as message, j}
						<div
							class="react-panels react-panel-{j} react-panel-rank-{i}"
						>
							<LikePanel
								model={j === 0 ? "A" : "B"}
								{disabled}
								Icon={ThumbUpActive}
								show={message.liked}
								value={likeValue}
								text="Qu'avez-vous apprécié dans la réponse ?"
								choices={positive_choices}
								handle_action={(selected) =>
									handle_action(i, j, message, selected)}
								commented={message.commented}
							/>
							<LikePanel
								model={j === 0 ? "A" : "B"}
								{disabled}
								Icon={ThumbDownActive}
								show={message.disliked}
								value={dislikeValue}
								text="Pourquoi la réponse ne convient-elle pas ?"
								choices={negative_choices}
								handle_action={(selected) =>
									handle_action(i, j, message, selected)}
								commented={message.commented}
							/>
						</div>
					{/each}
				</div>
			{/each}
		</div>
	{:else}
		<!-- TODO: remove this placeholder, if it appears it should be an error instead -->
		<div class="placeholder-content">
			{#if placeholder !== null}
				<div class="placeholder">
					<Markdown message={placeholder} {latex_delimiters} {root} />
				</div>
			{/if}
		</div>
	{/if}

	{#if hasError}
		<div class="fr-py-4w fr-mb-4w error rounded-tile fr-container">
			{#if errorString == "Context too long."}
				<h5>
					<span class="fr-icon-warning-fill" aria-hidden="true"
					></span> Oups, la conversation est trop longue pour un des modèles
				</h5>
				<p>
					Chaque modèle est limité dans la taille des conversations
					qu'il est capable de traiter.{#if groupedMessages.length > 1}&nbsp;Vous
						pouvez tout de même donner votre avis sur ces modèles ou
						recommencer une conversation avec deux nouveaux.{:else}
						&nbsp;Vous pouvez recommencer une conversation avec deux
						nouveaux modèles.
					{/if}
				</p>
				<p class="text-center">
					<!-- TODO: icone Recommencer -->
					<a
						class="btn purple-btn"
						href="../arene/?cgu_acceptees"
						target="_blank">Recommencer</a
					>
					<!-- TODO: Bouton "donner son avis" -->
				</p>
			{:else}
				<h3>
					<span class="fr-icon-warning-fill" aria-hidden="true"
					></span> Oups, erreur temporaire
				</h3>
				<p>
					Une erreur temporaire est survenue.<br />
					Vous pouvez tenter de réessayer de solliciter les modèles{#if groupedMessages.length > 1}&nbsp;ou
						bien conclure votre expérience en donnant votre avis sur
						les modèles{/if}.
					<span class="hidden">{errorString}</span>
				</p>
				<p class="text-center">
					<button
						class="fr-btn purple-btn"
						on:click={() => handle_retry_last()}
						disabled={generating || disabled}>Réessayer</button
					>
				</p>
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

<!-- Weird way to catch the comment if not validated but modal closed -->
<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<dialog
	aria-labelledby="modal-prefs"
	id="modal-prefs"
	class="fr-modal"
	on:blur={() => {
		sendComment(commenting);
	}}
	on:keydown={(e) => {
		if (e.key === "Escape") {
			sendComment(commenting);
		}
	}}
>
	<!-- on:click={() =>{sendComment(commenting)}} -->
	<div class="fr-container fr-container--fluid fr-container-md">
		<div class="fr-grid-row fr-grid-row--center">
			<div class="fr-col-12 fr-col-md-8 fr-col-lg-6">
				<div class="fr-modal__body">
					<div class="fr-modal__header">
						<button
							class="fr-btn--close fr-btn"
							title="Fermer la fenêtre modale"
							aria-controls="modal-prefs"
							on:click={() => sendComment(commenting)}
							>Fermer</button
						>
					</div>
					<div class="fr-modal__content">
						<p id="modal-prefs" class="modal-title">
							Ajouter des commentaires
						</p>
						<div>
							<textarea
								placeholder="Vous pouvez ajouter des précisions sur cette réponse du modèle {commenting_model}"
								class="fr-input"
								rows="4"
								bind:value={comment}
							></textarea>
							<button
								aria-controls="modal-prefs"
								class="btn purple-btn"
								on:click={() => sendComment(commenting)}
								>Envoyer</button
							>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</dialog>

<style>
	.modal-title {
		font-weight: 700;
		font-size: 1.1em;
	}

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

	.message-wrap :global(pre) {
		overflow-x: auto;
		max-width: 100%;
	}
	/*
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
		column-gap: 2em;
		grid-template-columns: 1fr;
		/* align-self: flex-start; */

		/* grid-template-columns: repeat(2, 1fr); */
	}

	/* On mobile, reorganize the panels */

	/* .react-panels.react-panel-0 {
		order: 1;
	} */
	.bot.right {
		order: 1;
	}

	.react-panels:global(.react-panel-0) {
		order: 0;
	}
	.react-panels:global(.react-panel-1) {
		order: 2;
	}

	@media (min-width: 48em) {
		.react-panels:global(.react-panel-0),
		.react-panels:global(.react-panel-1),
		.bot.right {
			order: inherit !important;
		}

		.bot-row {
			padding: 2em;
			grid-template-columns: 1fr 1fr;
			grid-auto-rows: 1fr auto;
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

	.fr-modal__content .purple-btn {
		float: right;
		margin: 2em 0 !important;
	}

	.fr-icon-warning-fill::before,
	.fr-icon-warning-fill::after {
		/* --warning-425-625 */
		color: #b34000;
		background-color: #b34000;
		-webkit-mask-image: url("../assets/dsfr/icons/system/fr--warning-fill.svg");
		mask-image: url("../assets/dsfr/icons/system/fr--warning-fill.svg");
	}
</style>
