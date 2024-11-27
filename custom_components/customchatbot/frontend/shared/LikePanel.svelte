<script lang="ts">
	import IconButton from "./IconButton.svelte";
	import ThumbDownActive from "./ThumbDownActive.svelte";
	import type { Gradio, SelectData } from "@gradio/utils";
	// import type { NormalisedMessage, TextMessage } from "../types";

	import {
		afterUpdate,
		createEventDispatcher,
		type SvelteComponent,
		type ComponentType,
		tick,
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

	export let handle_action: (selected: string | null) => void;

	export let value: (string | number)[] = [];
	export let old_value = value.slice();
	export let choices: [string, string | number][] = [
		["Utile", "useful"],
		["Complet", "complete"],
		["Créatif", "creative"],
		["Mise en forme claire", "clear-formatting"],
	]; // Example choices, adjust as necessary
	// $: disabled = !interactive;

	// let selected: "like" | "dislike" | null = null;

	function toggle_choice(choice: string | number): void {
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
	<p class="thumb-up-icon">
		<span>Qu'est-ce qui vous plaît ?<span></span></span>
	</p>
	{#each choices as [display_value, internal_value], i}
		<label class:selected={value.includes(internal_value)}>
			<input
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
	.like-panel {
		padding: 10px 24px;
		margin-top: 10px 0;
		background-color: white;
		border-color: #e5e5e5;
		border-style: dashed;
		border-width: 1px;
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
	}

	label.selected {
		background: #f5f5fe;
		color: #6a6af4;
		border: 1px #6a6af4 solid;
	}

	.thumb-up-icon span {
		font-weight: 700;
		color: #3a3a3a;
		vertical-align: top;
	}
	.thumb-up-icon {
		margin-bottom: 10px;
	}

	.thumb-up-icon::before {
		overflow: visible;
		content: "";
		padding-right: 24px;
		height: 20px;
		display: inline-block;
		background-size: 20px;
		/* background-size: url("./ThumbDownDefault.svelte"); */
		background-image: url("data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjIiIGhlaWdodD0iMjEiIHZpZXdCb3g9IjAgMCAyMiAyMSIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZmlsbC1ydWxlPSJldmVub2RkIiBjbGlwLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik0xMS4zODQgMC42ODk0ODZMMTMuMTk4IDEuNTk2NDlDMTQuMjQ5OCAyLjEyMjIyIDE0Ljc5MzEgMy4zMDk5MiAxNC41MDMgNC40NDk0OUwxMy42IDcuOTk4NDlIMjBDMjEuMTA0NiA3Ljk5ODQ5IDIyIDguODkzOTIgMjIgOS45OTg0OVYxMi4xMDI1QzIyLjAwMDMgMTIuMzYzOCAyMS45NDkzIDEyLjYyMjcgMjEuODUgMTIuODY0NUwxOC43NTUgMjAuMzc5NUMxOC42MDA2IDIwLjc1NDIgMTguMjM1MyAyMC45OTg1IDE3LjgzIDIwLjk5ODVIMUMwLjQ0NzcxNSAyMC45OTg1IDAgMjAuNTUwOCAwIDE5Ljk5ODVWOS45OTg0OUMwIDkuNDQ2MiAwLjQ0NzcxNSA4Ljk5ODQ5IDEgOC45OTg0OUg0LjQ4MkM0LjgwNjg4IDguOTk4NTcgNS4xMTE1NSA4Ljg0MDgzIDUuMjk5IDguNTc1NDlMMTAuNzUyIDAuODQ4NDg2QzEwLjg5NDQgMC42NDY2MTkgMTEuMTYzIDAuNTc5MDYxIDExLjM4NCAwLjY4OTQ4NlpNMTEuNjQzIDMuMDU2NDlMNi45MzMgOS43Mjg0OUM2LjY4MyAxMC4wODI1IDYuMzYzIDEwLjM3MjUgNiAxMC41ODY1VjE4Ljk5ODVIMTcuMTZMMjAgMTIuMTAyNVY5Ljk5ODQ5SDEzLjZDMTIuOTgyNyA5Ljk5ODQgMTIuNDAwMSA5LjcxMzMgMTIuMDIxMyA5LjIyNTk3QzExLjY0MjQgOC43Mzg2NSAxMS41MDk4IDguMTAzNyAxMS42NjIgNy41MDU0OUwxMi41NjUgMy45NTc0OUMxMi42MjMyIDMuNzI5NDUgMTIuNTE0NSAzLjQ5MTY3IDEyLjMwNCAzLjM4NjQ5TDExLjY0MyAzLjA1NjQ5WiIgZmlsbD0iIzZBNkFGNCIvPgo8L3N2Zz4K");
		background-repeat: no-repeat;
		margin-right: 0.2em;
	}
</style>
