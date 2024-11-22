<script lang="ts">
	import IconButton from "./IconButton.svelte";
	import ThumbDownActive from "./ThumbDownActive.svelte";
	import type { Gradio, SelectData } from "@gradio/utils";
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

	export let handle_action: (selected: string | null) => void;

	export let value: (string | number)[] = [];
	export let old_value = value.slice();
	export let choices: [string, string | number][] = [
		["Rien", "rien"],
		["Tout", "tout"],
	]; // Example choices, adjust as necessary
	// $: disabled = !interactive;

	// let selected: "like" | "dislike" | null = null;

	function toggle_choice(choice: string | number): void {
		if (value.includes(choice)) {
			value = value.filter((v) => v !== choice);
		} else {
			value = [...value, choice];
		}
		console.log("yo");
		console.log(choice);

		choice = "choice";
		handle_action(choice);
	}

	$: if (JSON.stringify(old_value) !== JSON.stringify(value)) {
		old_value = value;
		dispatch("change");
	}
</script>

<div class="rounded-tile">
	Qu'est-ce qui vous a déplu ?
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
