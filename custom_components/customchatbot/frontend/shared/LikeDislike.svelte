<script lang="ts">
	import IconButton from "./IconButton.svelte";
	import ThumbDownActive from "./ThumbDownActive.svelte";
	import ThumbDownDefault from "./ThumbDownDefault.svelte";
	import ThumbUpActive from "./ThumbUpActive.svelte";
	import ThumbUpDefault from "./ThumbUpDefault.svelte";

	export let handle_action: (selected: string | null) => void;
*
	let selected: "like" | "dislike" | null = null;
  </script>
  
  <IconButton
	border={true}
	Icon={selected === "dislike" ? ThumbDownActive : ThumbDownDefault}
	label={selected === "dislike" ? "clicked dislike" : "dislike"}
	highlight={selected === "dislike"}
	on:click={() => {
	  if (selected === "dislike") {
		selected = null;  // Un-select if already selected
	  } else {
		selected = "dislike";
	  }
	  handle_action(selected);
	}}
  />
  
  <IconButton
	border={true}
	Icon={selected === "like" ? ThumbUpActive : ThumbUpDefault}
	label={selected === "like" ? "clicked like" : "like"}
	highlight={selected === "like"}
	on:click={() => {
	  if (selected === "like") {
		selected = null;  // Un-select if already selected
	  } else {
		selected = "like";
	  }
	  handle_action(selected);
	}}
  />
  