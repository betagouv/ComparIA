<script lang="ts">
	import IconButton from "./IconButton.svelte";
	import ThumbDownActive from "./ThumbDownActive.svelte";
	import type { Gradio, SelectData } from "@gradio/utils";

	// export let handle_action: (selected: string | null) => void;

	export let gradio: Gradio<{
		change: never;
		select: SelectData;
		input: never;
		clear_status: LoadingStatus;
	}>;

	export let value: (string | number)[] = [];
	export let choices: [string, string | number][] = [("Rien", "rien"), ("Tout", "tout")];
	// $: disabled = !interactive;

	let selected: "like" | "dislike" | null = null;

	function toggle_choice(choice: string | number): void {
		if (value.includes(choice)) {
			value = value.filter((v) => v !== choice);
		} else {
			value = [...value, choice];
		}
		gradio.dispatch("input");
	}
</script>

<div class="rounded-tile">
	Qu'est-ce qui vous a déplu ?
	{#each choices as [display_value, internal_value], i}
		<label 
		class:selected={value.includes(internal_value)}>
			<input
				on:change={() => toggle_choice(internal_value)}
				on:input={(evt) =>
					gradio.dispatch("select", {
						index: i,
						value: internal_value,
						selected: evt.currentTarget.checked,
					})}
				on:keydown={(event) => {
					if (event.key === "Enter") {
						toggle_choice(internal_value);
						gradio.dispatch("select", {
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
<!-- 
<IconButton
	Icon={selected === "like" ? ThumbUpActive : ThumbUpDefault}
	label={selected === "like" ? "clicked like" : "like"}
	color={selected === "like"
		? "var(--color-accent)"
		: "var(--block-label-text-color)"}
	on:click={() => {
		selected = "like";
		handle_action(selected);
	}}
/> -->
