// function positive_mod(n: number, m: number): number {
// 	return ((n % m) + m) % m;
// }
type Item = string | number;


export interface ModeAndPromptData {
	prompt_value: string;
	mode: "random" | "custom" | "big-vs-small" | "small-models";
	custom_models_selection: Set<string>;
}

export interface Model {

	// [aya-expanse-8b]
	// simple_name = "Aya Expanse 8B"
	// organisation = "Cohere"
	// icon_path = "cohere.png"
	// friendly_size = "S"
	// distribution = "open-weights"
	// conditions = "copyleft"
	// params = 8
	// license = "CC-BY-NC-4.0"
	// description = "Aya Expanse 8B de Cohere, entreprise canadienne, est un petit modèle de la famille Command R qui a spécialement été entraîné sur un corpus multilingue." 

	id: string;
	simple_name: string;
	organisation: string;
	icon_path: string;
}

// export function handle_change(
// 	dispatch: any,
// 	value: string | number | (string | number)[] | undefined,
// ): void {
// 	dispatch("change", value);
// 	dispatch("input");
// }

// export function handle_shared_keys(
// 	e: KeyboardEvent,
// 	active_index: number | null,
// 	filtered_indices: number[]
// ): [boolean, number | null] {
// 	if (e.key === "Escape") {
// 		return [false, active_index];
// 	}
// 	if (e.key === "ArrowDown" || e.key === "ArrowUp") {
// 		if (filtered_indices.length >= 0) {
// 			if (active_index === null) {
// 				active_index =
// 					e.key === "ArrowDown"
// 						? filtered_indices[0]
// 						: filtered_indices[filtered_indices.length - 1];
// 			} else {
// 				const index_in_filtered = filtered_indices.indexOf(active_index);
// 				const increment = e.key === "ArrowUp" ? -1 : 1;
// 				active_index =
// 					filtered_indices[
// 					positive_mod(index_in_filtered + increment, filtered_indices.length)
// 					];
// 			}
// 		}
// 	}
// 	return [true, active_index];
// }
