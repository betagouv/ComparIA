<script context="module" lang="ts">
	export { default as BaseChatBot } from "./shared/ChatBot.svelte";
</script>

<script lang="ts">
	import type { Gradio, SelectData, LikeData } from "@gradio/utils";

	import ChatBot from "./shared/ChatBot.svelte";
	import type { UndoRetryData } from "./shared/utils";
	import { Block, BlockLabel } from "@gradio/atoms";
	import type { LoadingStatus } from "@gradio/statustracker";
	import { Chat } from "@gradio/icons";
	import { StatusTracker } from "@gradio/statustracker";
	import type {
		Message,
		TupleFormat,
		NormalisedMessage,
	} from "./types";

	import { normalise_tuples, normalise_messages } from "./shared/utils";

	export let elem_id = "";
	export let elem_classes: string[] = [];
	export let visible = true;
	export let value: TupleFormat | Message[] = [];
	export let scale: number | null = null;
	export let min_width: number | undefined = undefined;
	export let label: string;
	export let show_label = true;
	export let root: string;
	export let _selectable = true;
	export let likeable = false;
	export let show_share_button = false;
	export let rtl = false;
	export let show_copy_button = true;
	export let show_copy_all_button = false;
	export let sanitize_html = true;
	export let layout: "bubble" | "panel" = "bubble";
	export let type: "tuples" | "messages" = "tuples";
	export let render_markdown = true;
	export let line_breaks = true;
	export let autoscroll = true;
	export let _retryable = false;
	export let _undoable = false;
	export let latex_delimiters: {
		left: string;
		right: string;
		display: boolean;
	}[];
	export let gradio: Gradio<{
		change: typeof value;
		select: SelectData;
		share: ShareData;
		error: string;
		like: LikeData;
		clear_status: LoadingStatus;
		example_select: SelectData;
		retry: UndoRetryData;
		undo: UndoRetryData;
		clear: null;
	}>;

	let _value: NormalisedMessage[] | null = [];

	$: _value =
		type === "tuples"
			? normalise_tuples(value as TupleFormat, root)
			: normalise_messages(value as Message[], root);

	export let like_user_message = false;
	export let loading_status: LoadingStatus | undefined = undefined;
	export let height: number | string | undefined;
	export let min_height: number | string | undefined;
	export let max_height: number | string | undefined;
	export let placeholder: string | null = null;
	export let theme_mode: "system" | "light" | "dark";
</script>

<div class="wrapper {elem_classes}"
id={elem_id}
class:hidden={visible === false}
>
<!-- on:select={(e) => gradio.dispatch("select", e.detail)} -->

		<ChatBot
			selectable={_selectable}
			{likeable}
			{show_share_button}
			{show_copy_all_button}
			value={_value}
			{latex_delimiters}
			{render_markdown}
			{theme_mode}
			pending_message={loading_status?.status === "pending"}
			generating={loading_status?.status === "generating"}
			{rtl}
			{show_copy_button}
			{like_user_message}
			on:select={(e) => gradio.dispatch("select", e.detail)}
			on:change={() => gradio.dispatch("change", value)}
			on:like={(e) => gradio.dispatch("like", e.detail)}
			on:share={(e) => gradio.dispatch("share", e.detail)}
			on:error={(e) => gradio.dispatch("error", e.detail)}
			on:example_select={(e) =>
				gradio.dispatch("example_select", e.detail)}
			on:retry={(e) => gradio.dispatch("retry", e.detail)}
			on:undo={(e) => gradio.dispatch("undo", e.detail)}
			on:clear={() => {
				value = [];
				gradio.dispatch("clear");
			}}
			{sanitize_html}
			{line_breaks}
			{autoscroll}
			{layout}
			{placeholder}
			{_retryable}
			{_undoable}
			upload={(...args) => gradio.client.upload(...args)}
			_fetch={(...args) => gradio.client.fetch(...args)}
			load_component={gradio.load_component}
			msg_format={type}
			root={gradio.root}
		/>
</div>
<style>
	.wrapper {
		display: flex;
		position: relative;
		flex-direction: column;
		align-items: start;
		width: 100%;
		height: 100%;
		flex-grow: 1;
	}

	:global(.progress-text) {
		right: auto;
	}
</style>
