import gradio as gr


def stepper_html(title, step, total_steps):
    return f"""
    <div class="fr-stepper">
    <h2 class="fr-stepper__title">
        {title}
        <span class="fr-stepper__state">Étape {step} sur {total_steps}</span>
    </h2>
    <div class="fr-stepper__steps" data-fr-current-step="{step}" data-fr-steps="{total_steps}"></div>

</div>"""


header_html = """
    <header role="banner" class="">
  <div class="fr-header__body">
    <div class="">
      <div class="fr-header__body-row">
        <div class="fr-header__brand fr-enlarge-link">
          <div class="fr-header__brand-top">
            <div class="fr-header__logo">
              <p class="fr-logo">
                République
                <br>Française
              </p>
            </div>
          </div>
          <div class="fr-header__service">
            <a href="/" title="Accueil - LANGU:IA">
              <p class="fr-header__service-title">LANGU:IA
              <span class="fr-badge fr-badge--success fr-badge--no-icon">Beta</span>
              </p>
            </a>

            <p class="fr-header__service-tagline">L'arène francophone de comparaison de modèles conversationnels</p>
          </div>
        </div>

        <div class="fr-header__tools">
          <a title="À propos - ouvre une nouvelle fenêtre" href="https://beta.gouv.fr/startups/languia.html" target="_blank" rel="noopener external" class="fr-link fr-link--icon-right">À propos</a>
        </div>
      </div>
    </div>
  </div>

</header>
"""
