<script context="module" lang="ts">
	export { default as BaseRadio } from "./shared/Radio.svelte";
	export { default as BaseExample } from "./Example.svelte";
</script>

<script lang="ts">
	import type { Gradio, SelectData } from "@gradio/utils";
	import { StatusTracker } from "@gradio/statustracker";
	import type { LoadingStatus } from "@gradio/statustracker";
	import BaseRadio from "./shared/Radio.svelte";

	export let gradio: Gradio<{
		change: never;
		select: SelectData;
		input: never;
		clear_status: LoadingStatus;
	}>;

	// export let label = gradio.i18n("radio.radio");
	// export let info: string | undefined = undefined;
	export let elem_id = "";
	export let elem_classes: string[] = [];
	export let visible = true;
	export let value: string | null = null;
	export let choices: string[] = [];
	// export let show_label = true;
	// export let container = false;
	// export let scale: number | null = null;
	export let min_columns: number | undefined = 2;
	export let loading_status: LoadingStatus;
	export let interactive = true;

	let columns = Math.min(choices.length, 4); // max 4 columns

	function handle_change(): void {
		gradio.dispatch("change");
	}

	$: value, handle_change();

	$: disabled = !interactive;
</script>

<div
	id={elem_id}
	class="grid {elem_classes} {visible ? '' : 'hide'}"
	style="--columns: {columns};--min-columns: {min_columns}"
>
	<StatusTracker
		autoscroll={gradio.autoscroll}
		i18n={gradio.i18n}
		{...loading_status}
		on:clear_status={() => gradio.dispatch("clear_status", loading_status)}
	/>

	{#each choices as [display_value, internal_value], i (i)}
		<BaseRadio
			{display_value}
			{internal_value}
			bind:selected={value}
			{disabled}
			on:input={() => {
				gradio.dispatch("select", { value: internal_value, index: i });
				gradio.dispatch("input");
			}}
		/>
	{/each}
</div>

<style>
	.grid {
		display: grid;
		grid-template-columns: repeat(var(--min-columns), 1fr);
		gap: 0.625rem; 
		padding: 0.75rem; 
		margin: 0.75rem; 
	}
	@media (min-width: 48em) {
		.grid {
			gap: 1.5rem; 
			grid-template-columns: repeat(var(--columns), 1fr);
		}
	}
	/* .wrap {
		display: flex;
		flex-wrap: wrap;
		gap: var(--checkbox-label-gap);
	} */
</style>
