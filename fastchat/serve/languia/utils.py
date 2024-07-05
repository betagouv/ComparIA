import numpy as np
import os


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

def get_sample_weight(model, outage_models, sampling_weights, sampling_boost_models):
    if model in outage_models:
        return 0
    # Give a 1 weight if model not in weights
    weight = sampling_weights.get(model, 1)
    # weight = sampling_weights.get(model, 0)
    if model in sampling_boost_models:
        weight *= 5
    return weight

def get_battle_pair(
    models, battle_targets, outage_models, sampling_weights, sampling_boost_models
):
    if len(models) == 1:
        return models[0], models[0]

    model_weights = []
    for model in models:
        weight = get_sample_weight(
            model, outage_models, sampling_weights, sampling_boost_models
        )
        model_weights.append(weight)
    total_weight = np.sum(model_weights)
    model_weights = model_weights / total_weight
    chosen_idx = np.random.choice(len(models), p=model_weights)
    chosen_model = models[chosen_idx]
    # for p, w in zip(models, model_weights):
    #     print(p, w)

    rival_models = []
    rival_weights = []
    for model in models:
        if model == chosen_model:
            continue
        weight = get_sample_weight(
            model, outage_models, sampling_weights, sampling_boost_models
        )
        if (
            weight != 0
            and chosen_model in battle_targets
            and model in battle_targets[chosen_model]
        ):
            # boost to 50% chance
            weight = total_weight / len(battle_targets[chosen_model])
        rival_models.append(model)
        rival_weights.append(weight)
    # for p, w in zip(rival_models, rival_weights):
    #     print(p, w)
    rival_weights = rival_weights / np.sum(rival_weights)
    rival_idx = np.random.choice(len(rival_models), p=rival_weights)
    rival_model = rival_models[rival_idx]

    swap = np.random.randint(2)
    if swap == 0:
        return chosen_model, rival_model
    else:
        return rival_model, chosen_model


def get_matomo_js(matomo_url, matomo_id):
    return f"""
    <!-- Matomo -->
<script>
  var _paq = window._paq = window._paq || [];
  /* tracker methods like "setCustomDimension" should be called before "trackPageView" */
  _paq.push(['trackPageView']);
  _paq.push(['enableLinkTracking']);
  _paq.push(['HeatmapSessionRecording::enable'])
  (function() {{
    var u="{matomo_url}/";
    _paq.push(['setTrackerUrl', u+'matomo.php']);
    _paq.push(['setSiteId', '{os.getenv("MATOMO_ID")}']);
    var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
    g.async=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
  }})();
</script>
<noscript><p><img referrerpolicy="no-referrer-when-downgrade" src="{matomo_url}/matomo.php?idsite={matomo_id}&amp;rec=1" style="border:0;" alt="" /></p></noscript>
<!-- End Matomo Code -->
    """


def add_chosen_badge(side, which_model_radio):
    if (side == "a" and which_model_radio == "leftvote") or (
        side == "b" and which_model_radio == "rightvote"
    ):
        return """
         <span class="fr-badge">Votre choix</span>
         """
    else:
        return ""


def build_reveal_html(model_a, model_b, which_model_radio):
    reveal_html = f"""<div><div class="fr-tile"><h2>Modèle A : {model_a}</h2>"""
    reveal_html += add_chosen_badge("a", which_model_radio)
    reveal_html += f"""</div>
    <div class="fr-tile><h2>Modèle B : {model_b}</h2>
    """
    reveal_html += add_chosen_badge("b", which_model_radio)
    reveal_html += "</div></div>"

    print(reveal_html)
    return reveal_html
