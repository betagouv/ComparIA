<script lang="ts">
	import {
		beforeUpdate,
		afterUpdate,
		createEventDispatcher,
		tick,
	} from "svelte";
	import { BlockTitle } from "@gradio/atoms";
	import { Copy, Check } from "@gradio/icons";
	import { fade } from "svelte/transition";
	import type { SelectData } from "@gradio/utils";

	// import "@gouvfr/dsfr/dist/scheme/scheme.css";
	// import "@gouvfr/dsfr/dist/core/core.css";
	// import "@gouvfr/dsfr/dist/component/form/form.css";
	// import "@gouvfr/dsfr/dist/component/link/link.css";
	// import "@gouvfr/dsfr/dist/component/button/button.css";
	// import "@gouvfr/dsfr/dist/component/input/input.css";

	export let value = "";
	export let value_is_output = false;
	export let lines = 1;
	export let placeholder = "Type here...";
	// export let info: string | undefined = undefined;
	export let disabled = false;
	// export let container = true;
	export let max_lines: number;
	export let rtl = false;
	export let autofocus = false;
	export let text_align: "left" | "right" | undefined = undefined;
	export let autoscroll = true;
	export let visible = true;
	export let elem_id = "";
	export let elem_classes: string[] = [];

	let el: HTMLTextAreaElement | HTMLInputElement;
	let copied = false;
	let timer: NodeJS.Timeout;
	let can_scroll: boolean;
	let previous_scroll_top = 0;
	let user_has_scrolled_up = false;

	$: value, el && lines !== max_lines && resize({ target: el });

	$: if (value === null) value = "";

	const dispatch = createEventDispatcher<{
		change: string;
		submit: undefined;
		blur: undefined;
		select: SelectData;
		input: undefined;
		focus: undefined;
	}>();

	beforeUpdate(() => {
		can_scroll =
			el && el.offsetHeight + el.scrollTop > el.scrollHeight - 100;
	});

	const scroll = (): void => {
		if (can_scroll && autoscroll && !user_has_scrolled_up) {
			el.scrollTo(0, el.scrollHeight);
		}
	};

	function handle_input(): void {
		dispatch("change", value);
		if (!value_is_output) {
			dispatch("input");
		}
	}
	afterUpdate(() => {
		if (autofocus) {
			el.focus();
		}
		if (can_scroll && autoscroll) {
			scroll();
		}
		value_is_output = false;
	});
	$: value, handle_input();

	async function handle_copy(): Promise<void> {
		if ("clipboard" in navigator) {
			await navigator.clipboard.writeText(value);
			copy_feedback();
		}
	}

	function copy_feedback(): void {
		copied = true;
		if (timer) clearTimeout(timer);
		timer = setTimeout(() => {
			copied = false;
		}, 1000);
	}

	function handle_select(event: Event): void {
		const target: HTMLTextAreaElement | HTMLInputElement = event.target as
			| HTMLTextAreaElement
			| HTMLInputElement;
		const text = target.value;
		const index: [number, number] = [
			target.selectionStart as number,
			target.selectionEnd as number,
		];
		dispatch("select", { value: text.substring(...index), index: index });
	}

	async function handle_keypress(e: KeyboardEvent): Promise<void> {
		await tick();
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			dispatch("submit");
		}
	}

	function handle_scroll(event: Event): void {
		const target = event.target as HTMLElement;
		const current_scroll_top = target.scrollTop;
		if (current_scroll_top < previous_scroll_top) {
			user_has_scrolled_up = true;
		}
		previous_scroll_top = current_scroll_top;

		const max_scroll_top = target.scrollHeight - target.clientHeight;
		const user_has_scrolled_to_bottom =
			current_scroll_top >= max_scroll_top;
		if (user_has_scrolled_to_bottom) {
			user_has_scrolled_up = false;
		}
	}

	async function resize(
		event: Event | { target: HTMLTextAreaElement | HTMLInputElement },
	): Promise<void> {
		await tick();
		if (lines === max_lines) return;

		let max =
			max_lines === undefined
				? false
				: max_lines === undefined // default
					? 21 * 11
					: 21 * (max_lines + 1);
		let min = 21 * (lines + 1);

		const target = event.target as HTMLTextAreaElement;
		target.style.height = "1px";

		let scroll_height;
		if (max && target.scrollHeight > max) {
			scroll_height = max;
		} else if (target.scrollHeight < min) {
			scroll_height = min;
		} else {
			scroll_height = target.scrollHeight;
		}

		target.style.height = `${scroll_height}px`;
	}

	function text_area_resize(
		_el: HTMLTextAreaElement,
		_value: string,
	): any | undefined {
		if (lines === max_lines) return;
		_el.style.overflowY = "scroll";
		_el.addEventListener("input", resize);

		// if (!_value.trim()) return;
		resize({ target: _el });

		return {
			destroy: () => _el.removeEventListener("input", resize),
		};
	}
</script>

<!-- svelte-ignore a11y-autofocus -->
<label class="container fr-label {elem_classes.join(' ')}">
	{#if lines === 1 && max_lines === 1}
		<input
			data-testid="textbox"
			type="text"
			id={elem_id}
			class:hidden={visible === false}
			class="scroll-hide fr-input"
			dir={rtl ? "rtl" : "ltr"}
			bind:value
			bind:this={el}
			{placeholder}
			{disabled}
			{autofocus}
			on:keypress={handle_keypress}
			on:blur
			on:select={handle_select}
			on:focus
			style={text_align ? "text-align: " + text_align : ""}
		/>
	{:else}
		<textarea
			data-testid="textbox"
			use:text_area_resize={value}
			class:hidden={visible === false}
			class="scroll-hide fr-input"
			dir={rtl ? "rtl" : "ltr"}
			bind:value
			bind:this={el}
			{placeholder}
			rows={lines}
			{disabled}
			{autofocus}
			on:keypress={handle_keypress}
			on:blur
			on:select={handle_select}
			on:focus
			on:scroll={handle_scroll}
			style={text_align ? "text-align: " + text_align : ""}
		/>
	{/if}
</label>

<style>
	textarea.fr-input {
		background-color: white !important;
		border-radius: 0.5em 0.5em 0 0;
		border: 1px solid #e5e5e5 !important;
		/* border: 1px 1px 0 1px solid #e5e5e5 !important; */
		/* min-height: 4rem !important; */
		box-shadow: inset 0 -2px 0 0 #6a6af4 !important;
		outline: none !important;
		outline-offset: 0 !important;
	}

	@media (min-width: 48em) {
		textarea.fr-input {
			min-height: 2.5rem !important;
		}
	}
</style>
