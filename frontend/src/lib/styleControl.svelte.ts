/**
 * Global "Contrôle du style" (Style Control) toggle.
 *
 * On by default: the leaderboard shows the style-controlled Bradley-Terry
 * ranking, where answer length and markdown formatting are regressed out so the
 * score reflects substance over presentation. Turning it off swaps in the plain
 * ranking (see `DatasetData.uncontrolled`). A module-level singleton so the
 * choice is shared across every ranking view and survives tab switches.
 */
class StyleControl {
  enabled = $state(true)
}

export const styleControl = new StyleControl()
