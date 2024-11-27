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
		["Incorrect", "incorrect"],
		["Superficiel", "superficial"],
		["Instructions non suivies", "instructions-not-followed"],
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

	<div class="dislike-panel" class:hidden={show === false}>
		<p class="thumb-down-icon">
			<span>Qu'est-ce qui ne va pas ?<span></span></span>
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
	.dislike-panel {
		padding: 10px 24px;
		margin-top: 10px;
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

	.thumb-down-icon span {
		font-weight: 700;
		color: #3a3a3a;
		vertical-align: top;
	}
	.thumb-down-icon {
		margin-bottom: 10px;
	}

	.thumb-down-icon::before {
		overflow: visible;
		content: "";
		padding-right: 24px;
		height: 20px;
		display: inline-block;
		background-size: 20px;
		/* background-size: url("./ThumbDownDefault.svelte"); */
		background-image: url("data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZmlsbC1ydWxlPSJldmVub2RkIiBjbGlwLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik0yMiAzQzIyLjU1MjMgMyAyMyAzLjQ0NzcyIDIzIDRWMTRDMjMgMTQuNTUyMyAyMi41NTIzIDE1IDIyIDE1SDE4LjUxOEMxOC4xOTMxIDE0Ljk5OTkgMTcuODg4NSAxNS4xNTc3IDE3LjcwMSAxNS40MjNMMTIuMjQ4IDIzLjE0OUMxMi4xMDU2IDIzLjM1MDkgMTEuODM3IDIzLjQxODQgMTEuNjE2IDIzLjMwOEw5LjgwMiAyMi40QzguNzUwMTYgMjEuODc0MyA4LjIwNjg5IDIwLjY4NjYgOC40OTcgMTkuNTQ3TDkuNCAxNkgzQzEuODk1NDMgMTYgMSAxNS4xMDQ2IDEgMTRWMTEuODk2QzAuOTk5NzMyIDExLjYzNDYgMS4wNTA2OSAxMS4zNzU4IDEuMTUgMTEuMTM0TDQuMjQ2IDMuNjJDNC4zOTk5NiAzLjI0NTIzIDQuNzY0ODQgMy4wMDA0IDUuMTcgM0gyMlpNMTcgNUg1Ljg0TDMgMTEuODk2VjE0SDkuNEMxMC4wMTczIDE0LjAwMDEgMTAuNTk5OSAxNC4yODUyIDEwLjk3ODcgMTQuNzcyNUMxMS4zNTc2IDE1LjI1OTggMTEuNDkwMiAxNS44OTQ4IDExLjMzOCAxNi40OTNMMTAuNDM1IDIwLjA0MUMxMC4zNzY4IDIwLjI2OSAxMC40ODU1IDIwLjUwNjggMTAuNjk2IDIwLjYxMkwxMS4zNTcgMjAuOTQyTDE2LjA2NyAxNC4yN0MxNi4zMTcgMTMuOTE2IDE2LjYzNyAxMy42MjYgMTcgMTMuNDEyVjVaIiBmaWxsPSIjNkE2QUY0Ii8+Cjwvc3ZnPgo=");
		/* background-position-y: 6px; */
		background-repeat: no-repeat;
		margin-right: 0.2em;
	}
</style>
