<script lang="ts">
	import type { Gradio, SelectData } from "@gradio/utils";
	// import type { NormalisedMessage, TextMessage } from "../types";

	import "@gouvfr/dsfr/dist/component/modal/modal.css";

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

	let element;
	export let show: boolean;

	export let handle_action: (value: string | null | string[]) => void;

	// import { type ComponentType } from "svelte";
	export let Icon: ComponentType;
	export let text: string;
	export let commented: boolean = false;
	export let disabled: boolean = false;
	export let model: string = "";
	export let value: string[] = [];
	export let old_value = value.slice();
	export let choices: [string, string][] = [
		["Utile", "useful"],
		["Complet", "complete"],
		["Créatif", "creative"],
		["Mise en forme claire", "clear-formatting"],
	];

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

	$: if (show) {
		if (element) element.scrollIntoView({ behavior: "smooth" });
	}
</script>

<div bind:this={element} class="like-panel" class:hidden={show === false}>
	<p class="thumb-icon inline-svg">
		<svelte:component this={Icon} />
		<span>{text}</span>
	</p>
	{#each choices as [display_value, internal_value], i}
		<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
		<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
		<label
			class:disabled
			class:selected={value.includes(internal_value)}
			aria-checked={value.includes(internal_value)}
			aria-disabled={disabled ? "true" : "false"}
			tabindex="0"
			on:keydown={(event) => {
				if (event.key === "Enter" || event.key === " ") {
					toggle_choice(internal_value);
					dispatch("select", {
						index: i,
						value: internal_value,
						selected: !value.includes(internal_value),
					});
				}
			}}
		>
			<input
				{disabled}
				on:change={() => toggle_choice(internal_value)}
				on:input={(evt) =>
					dispatch("select", {
						index: i,
						value: internal_value,
						selected: evt.currentTarget.checked,
					})}
				checked={value.includes(internal_value)}
				type="checkbox"
				name={internal_value?.toString()}
				title={`${display_value} pour le modèle ${model}`}
				aria-checked={value.includes(internal_value)}
			/>
			<span
				class="ml-2"
				title={`${display_value} pour le modèle ${model}`}
				>{display_value}</span
			>
		</label>
	{/each}
	<button
		{disabled}
		class:selected={commented}
		data-fr-opened="false"
		aria-controls="modal-prefs"
		on:click={() => {
			commented = true;
			handle_action("commenting");
		}}>Autre…</button
	>
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
		line-height: 3em;
		padding: 4px 10px;
	}
	label,
	button {
		/* font-size: 0.875em; */
		border-radius: 1.5rem !important;
		background: white;
		color: #606367 !important;
		border: 1px #dadce0 solid !important;
		font-weight: 500;
		margin-right: 10px;
		cursor: pointer;
	}
	button {
		padding: 3px 10px;
	}

	label.selected,
	label:active,
	button:active,
	button.selected {
		background: #f5f5fe !important;
		color: #6a6af4 !important;
		border: 1px #6a6af4 solid !important;
	}

	label:hover,
	button:hover {
		background-color: var(--hover);
	}

	.thumb-icon {
		font-weight: 700;
		color: #3a3a3a;
		margin-bottom: 5px !important;
	}

	label.disabled.selected,
	button[disabled].selected {
		opacity: 0.5;
		box-shadow: none;
		background-color: #eee !important;
		border: 1px solid #606367 !important;
		color: #3a3a3a !important;
	}

	label.disabled:hover,
	button[disabled]:hover {
		cursor: not-allowed;
	}
</style>
