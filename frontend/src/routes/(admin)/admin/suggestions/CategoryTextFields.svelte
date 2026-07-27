<script lang="ts">
  let {
    title = $bindable(),
    description = $bindable(),
    tooltip = $bindable(),
    titleLabel,
    descriptionLabel,
    descriptionHint,
    tooltipLabel,
    tooltipHint,
    titleMaximumHint,
    descriptionMaximumHint,
    tooltipMaximumHint
  }: {
    title: string
    description: string
    tooltip: string
    titleLabel: string
    descriptionLabel: string
    descriptionHint: string
    tooltipLabel: string
    tooltipHint: string
    titleMaximumHint: string
    descriptionMaximumHint: string
    tooltipMaximumHint: string
  } = $props()
</script>

<div class="fr-input-group">
  <label class="fr-label" for="suggestion-category-title">
    {titleLabel}
    <span id="suggestion-category-title-limit" class="fr-hint-text">{titleMaximumHint}</span>
  </label>
  <input
    id="suggestion-category-title"
    class="fr-input"
    bind:value={title}
    required
    maxlength="100"
    aria-describedby="suggestion-category-title-limit"
  />
</div>

<div class="fr-input-group">
  <label class="fr-label" for="suggestion-category-description">
    {descriptionLabel}
    <span id="suggestion-category-description-hint" class="fr-hint-text">{descriptionHint}</span>
    <span id="suggestion-category-description-limit" class="fr-hint-text">
      {descriptionMaximumHint}
    </span>
  </label>
  <textarea
    id="suggestion-category-description"
    class="fr-input"
    bind:value={description}
    required
    maxlength="300"
    aria-describedby="suggestion-category-description-hint suggestion-category-description-limit"
  ></textarea>
</div>

<div class="fr-input-group">
  <label class="fr-label" for="suggestion-category-tooltip">
    {tooltipLabel}
    <span id="suggestion-category-tooltip-hint" class="fr-hint-text">{tooltipHint}</span>
    <span id="suggestion-category-tooltip-limit" class="fr-hint-text">
      {tooltipMaximumHint}
    </span>
  </label>
  <textarea
    id="suggestion-category-tooltip"
    class="fr-input"
    bind:value={tooltip}
    maxlength="300"
    aria-describedby="suggestion-category-tooltip-hint suggestion-category-tooltip-limit suggestion-category-messages"
  ></textarea>
</div>
