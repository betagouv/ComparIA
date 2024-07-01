<svelte:options accessors={true} />

<script lang="ts">

    import '@gouvfr/dsfr/dist/scheme/scheme.css'
    import '@gouvfr/dsfr/dist/core/core.css'
    import '@gouvfr/dsfr/dist/component/form/form.css'
    import '@gouvfr/dsfr/dist/component/link/link.css'
    import '@gouvfr/dsfr/dist/component/button/button.css'
    import '@gouvfr/dsfr/dist/component/input/input.css'

	import type { Gradio } from "@gradio/utils";
	import { BlockTitle } from "@gradio/atoms";
	import { Block } from "@gradio/atoms";
	import { StatusTracker } from "@gradio/statustracker";
	import type { LoadingStatus } from "@gradio/statustracker";
	import { tick } from "svelte";

	export let gradio: Gradio<{
		change: never;
		submit: never;
		input: never;
		clear_status: LoadingStatus;
	}>;
	export let label = "Textbox";
	export let elem_id = "";
	export let elem_classes: string[] = [];
	export let visible = true;
	export let value = "";
	export let placeholder = "";
	export let show_label: boolean;
	export let scale: number | null = null;
	export let min_width: number | undefined = undefined;
	export let loading_status: LoadingStatus | undefined = undefined;
	export let value_is_output = false;
	export let interactive: boolean;
	export let rtl = false;

	let el: HTMLTextAreaElement | HTMLInputElement;
	const container = true;

	function handle_change(): void {
		gradio.dispatch("change");
		if (!value_is_output) {
			gradio.dispatch("input");
		}
	}

	async function handle_keypress(e: KeyboardEvent): Promise<void> {
		await tick();
		if (e.key === "Enter") {
			e.preventDefault();
			gradio.dispatch("submit");
		}
	}

	$: if (value === null) value = "";

	// When the value changes, dispatch the change event via handle_change()
	// See the docs for an explanation: https://svelte.dev/docs/svelte-components#script-3-$-marks-a-statement-as-reactive
	$: value, handle_change();
</script>

<Block
	{visible}
	{elem_id}
	{elem_classes}
	{scale}
	{min_width}
	allow_overflow={false}
	padding={true}
>
	{#if loading_status}
		<StatusTracker
			autoscroll={gradio.autoscroll}
			i18n={gradio.i18n}
			{...loading_status}
			on:clear_status={() => gradio.dispatch("clear_status", loading_status)}
		/>
	{/if}

	<label class:container class="fr-label">
		<BlockTitle {show_label} info={undefined}>{label}</BlockTitle>

		<input
			data-testid="textbox"
			type="text"
			class="fr-input"
			bind:value
			bind:this={el}
			{placeholder}
			disabled={!interactive}
			dir={rtl ? "rtl" : "ltr"}
			on:keypress={handle_keypress}
		/>
	</label>
</Block>

<style>
</style>
