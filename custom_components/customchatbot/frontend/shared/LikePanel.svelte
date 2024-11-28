<script lang="ts">
	import type { Gradio, SelectData } from "@gradio/utils";
	// import type { NormalisedMessage, TextMessage } from "../types";

	import {
		// afterUpdate,
		type ComponentType,
		createEventDispatcher,
		// type SvelteComponent,
		// tick,
		onMount,
	} from "svelte";

	const dispatch = createEventDispatcher<{
		change: undefined;
		select: SelectData;
		input: undefined;
	}>();

	export let show: boolean; // Define the 'show' prop as a boolean
	// export let message: NormalisedMessage | NormalisedMessage[];
	// export let prefs: string[] = [];
	export let handle_action: (value: string | null | string[]) => void;

	// import { type ComponentType } from "svelte";
	export let Icon: ComponentType;
	export let text: string;
	// export let comment: string | undefined;
	export let commented: boolean = false;
	export let disabled: boolean = false;
	export let value: string[] = [];
	export let old_value = value.slice();
	export let choices: [string, string][] = [
		["Utile", "useful"],
		["Complet", "complete"],
		["Créatif", "creative"],
		["Mise en forme claire", "clear-formatting"],
	]; // Example choices, adjust as necessary
	// $: disabled = !interactive;

	// let selected: "like" | "dislike" | null = null;

	function toggle_choice(choice: string): void {
		if (value.includes(choice)) {
			value = value.filter((v) => v !== choice);
		} else {
			value = [...value, choice];
		}
	}

	$: if (JSON.stringify(old_value) !== JSON.stringify(value)) {
		old_value = value;
		handle_action(value);
	}
</script>

<div class="like-panel" class:hidden={show === false}>
	<p class="thumb-icon inline-svg">
		<svelte:component this={Icon} />
		<span>{text}</span>
	</p>
	{#each choices as [display_value, internal_value], i}
		<label class:disabled class:selected={value.includes(internal_value)}>
			<input
				{disabled}
				on:change={() => toggle_choice(internal_value)}
				on:input={(evt) =>
					dispatch("select", {
						index: i,
						value: internal_value,
						selected: evt.currentTarget.checked,
					})}
				on:keydown={(event) => {
					if (event.key === "Enter") {
						toggle_choice(internal_value);
						dispatch("select", {
							index: i,
							value: internal_value,
							selected: !value.includes(internal_value),
						});
					}
				}}
				checked={value.includes(internal_value)}
				type="checkbox"
				name={internal_value?.toString()}
				title={internal_value?.toString()}
			/>
			<span class="ml-2">{display_value}</span>
		</label>
	{/each}
</div>

<style>
	.inline-svg :global(svg) {
		display: inline;
	}

	.like-panel {
		padding: 1em 1.5em 1em;
		margin-bottom: 1em;
		background-color: white;
		border-color: #e5e5e5;
		border-style: dashed;
		border-width: 1.5px;
		border-radius: 0.25rem;
	}
	[type="checkbox"] {
		display: none;
	}

	label span {
		margin-left: 0;
	}

	label {
		/* font-size: 0.875em; */
		border-radius: 1.5rem;
		background: white;
		color: #606367;
		border: 1px #dadce0 solid;
		font-weight: 500;
		padding: 4px 10px;
		margin-right: 10px;
		line-height: 3em;
	}

	label.selected {
		background: #f5f5fe;
		color: #6a6af4;
		border: 1px #6a6af4 solid;
	}

	.thumb-icon {
		font-weight: 700;
		color: #3a3a3a;
		margin-bottom: 5px !important;
	}

	label.disabled.selected {
		opacity: 0.5;
		box-shadow: none;
		background-color: #eee !important;
		border: 1px solid #606367 !important;
		color: #3a3a3a !important;
	}

	label.disabled:hover {
		cursor: not-allowed;
	}
</style>
