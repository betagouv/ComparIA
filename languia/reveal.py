import logging
from languia.utils import get_model_extra_info, count_output_tokens, get_chosen_model

from jinja2 import Environment, FileSystemLoader

from ecologits.tracers.utils import llm_impacts, compute_llm_impacts, electricity_mixes

size_desc = {
    "XS": "Les modèles très petits, avec moins de 7 milliards de paramètres, sont les moins complexes et les plus économiques en termes de ressources, offrant des performances suffisantes pour des tâches simples comme la classification de texte.",
    "S": "Un modèle de petit gabarit est moins complexe et coûteux en ressources par rapport aux modèles plus grands, tout en offrant une performance suffisante pour diverses tâches (résumé, traduction, classification de texte...)",
    "M": "Les modèles moyens offrent un bon équilibre entre complexité, coût et performance : ils sont beaucoup moins consommateurs de ressources que les grands modèles tout en étant capables de gérer des tâches complexes telles que l'analyse de sentiment ou le raisonnement.",
    "L": "Les grands modèles nécessitent des ressources significatives, mais offrent les meilleures performances pour des tâches avancées comme la rédaction créative, la modélisation de dialogues et les applications nécessitant une compréhension fine du contexte.",
    "XL": "Ces modèles dotés de plusieurs centaines de milliards de paramètres sont les plus complexes et avancés en termes de performance et de précision. Les ressources de calcul et de mémoire nécessaires pour déployer ces modèles sont telles qu’ils sont destinés aux applications les plus avancées et aux environnements hautement spécialisés.",
}

license_desc = {
    "MIT": "La licence MIT est une licence de logiciel libre permissive : elle permet à quiconque de réutiliser, modifier et distribuer le modèle, même à des fins commerciales, sous réserve d'inclure la licence d'origine et les mentions de droits d'auteur.",
    "Apache 2.0": "Cette licence permet d'utiliser, modifier et distribuer librement, même à des fins commerciales. Outre la liberté d’utilisation, elle garantit la protection juridique en incluant une clause de non-atteinte aux brevets et la transparence : toutes les modifications doivent être documentées et sont donc traçables.",
    "Gemma": "Cette licence est conçue pour encourager l'utilisation, la modification et la redistribution des logiciels mais inclut une clause stipulant que toutes les versions modifiées ou améliorées doivent être partagée avec la communauté sous la même licence, favorisant ainsi la collaboration et la transparence dans le développement logiciel.",
    "Llama 3 Community": "Cette licence permet d'utiliser, modifier et distribuer librement le code avec attribution, mais impose des restrictions pour les opérations dépassant 700 millions d'utilisateurs mensuels et interdit la réutilisation du code ou des contenus générés pour l’entraînement ou l'amélioration de modèles concurrents, protégeant ainsi les investissements technologiques et la marque de Meta.",
    "Llama 3.1": "Cette licence permet d'utiliser, reproduire, modifier et distribuer librement le code avec attribution, mais impose des restrictions pour les opérations dépassant 700 millions d'utilisateurs mensuels. La réutilisation du code ou des contenus générés pour l’entraînement ou l'amélioration de modèles dérivés est autorisée à condition d’afficher “built with llama” et d’inclure “Llama” dans leur nom pour toute distribution.",
    "CC-BY-NC-4.0": "Cette licence permet de partager et adapter le contenu à condition de créditer l'auteur, mais interdit toute utilisation commerciale. Elle offre une flexibilité pour les usages non commerciaux tout en protégeant les droits de l'auteur.",
    "propriétaire Gemini": "Le modèle est disponible sous licence payante et accessible via l'API Gemini disponible sur les plateformes Google AI Studio et Vertex AI, nécessitant un paiement à l'utilisation basé sur le nombre de tokens traités.",
    "propriétaire Liquid": "Le modèle est disponible sous licence payante et accessible via API sur les plateformes de la société Liquid AI, nécessitant un paiement à l'utilisation basé sur le nombre de tokens traités.",
    "propriétaire OpenAI": "Le modèle est disponible sous licence payante et accessible via API sur les plateformes de la société OpenAI, nécessitant un paiement à l'utilisation basé sur le nombre de tokens traités.",
    "Mistral AI Non-Production": "Cette licence permet de partager et adapter le contenu à condition de créditer l'auteur, mais interdit toute utilisation commerciale. Elle offre une flexibilité pour les usages non commerciaux tout en protégeant les droits de l'auteur.",
}

license_attrs = {
    # Utilisation commerciale
    # Modification autorisée
    # Attribution requise
    # "MIT": {"commercial": True, "can_modify": True, "attribution": True},
    # "Apache 2.0": {"commercial": True, "can_modify": True, "attribution": True},
    # "Gemma": {"copyleft": True},
    "Llama 3 Community": {"warning_commercial": True},
    "Llama 3.1": {"warning_commercial": True},
    "CC-BY-NC-4.0": {"prohibit_commercial": True},
    "Mistral AI Non-Production": {"prohibit_commercial": True},
}


def calculate_lightbulb_consumption(impact_energy_value):
    """
    Calculates the energy consumption of a 5W LED light and determines the most sensible time unit.

    Args:
      impact_energy_value: Energy consumption in kilowatt-hours (kWh).

    Returns:
      A tuple containing:
        - An integer representing the consumption time.
        - A string representing the most sensible time unit ('days', 'hours', 'minutes', or 'seconds').
    """

    # Calculate consumption time using Wh
    watthours = impact_energy_value * 1000
    consumption_hours = watthours / 5
    consumption_days = watthours / (5 * 24)
    consumption_minutes = watthours * 60 / (5)
    consumption_seconds = watthours * 60 * 60 / (5)

    # Determine the most sensible unit based on magnitude
    if consumption_days >= 1:
        return int(consumption_days), "j"
    elif consumption_hours >= 1:
        return int(consumption_hours), "h"
    elif consumption_minutes >= 1:
        return int(consumption_minutes), "min"
    else:
        return int(consumption_seconds), "s"


def calculate_streaming_hours(impact_gwp_value):
    """
    Calculates equivalent streaming hours and determines a sensible time unit.

    Args:
      impact_gwp_value: CO2 emissions in kilograms.

    Returns:
      A tuple containing:
        - An integer representing the streaming hours.
        - A string representing the most sensible time unit ('days', 'hours', 'minutes', or 'seconds').
    """

    # Calculate streaming hours: https://impactco2.fr/outils/usagenumerique/streamingvideo
    streaming_hours = (impact_gwp_value * 10000) / 317

    # Determine sensible unit based on magnitude
    if streaming_hours >= 24:  # 1 day in hours
        return int(streaming_hours / 24), "j"
    elif streaming_hours >= 1:
        return int(streaming_hours), "h"
    elif streaming_hours * 60 >= 1:
        return int(streaming_hours * 60), "min"
    else:
        return int(streaming_hours * 60 * 60), "s"


def build_reveal_html(conv_a, conv_b, which_model_radio):
    from languia.config import models_extra_info

    logger = logging.getLogger("languia")

    model_a = get_model_extra_info(conv_a.model_name, models_extra_info)
    model_b = get_model_extra_info(conv_b.model_name, models_extra_info)
    logger.debug("output_tokens: " + str(conv_a.output_tokens))
    logger.debug("output_tokens: " + str(conv_b.output_tokens))

    # TODO: Improve fake token counter: 4 letters by token: https://genai.stackexchange.com/questions/34/how-long-is-a-token
    model_a_tokens = (
        conv_a.output_tokens
        if conv_a.output_tokens and conv_a.output_tokens != 0
        else count_output_tokens(conv_a.messages)
    )

    model_b_tokens = (
        conv_b.output_tokens
        if conv_b.output_tokens and conv_b.output_tokens != 0
        else count_output_tokens(conv_b.messages)
    )
    # TODO:
    # request_latency_a = conv_a.conv.finish_tstamp - conv_a.conv.start_tstamp
    # request_latency_b = conv_b.conv.finish_tstamp - conv_b.conv.start_tstamp
    model_a_impact = get_llm_impact(model_a, conv_a.model_name, model_a_tokens, None)
    model_b_impact = get_llm_impact(model_b, conv_b.model_name, model_b_tokens, None)

    env = Environment(loader=FileSystemLoader("templates"))

    template = env.get_template("reveal.html")
    chosen_model = get_chosen_model(which_model_radio)
    lightbulb_a, lightbulb_a_unit = calculate_lightbulb_consumption(
        model_a_impact.energy.value
    )
    lightbulb_b, lightbulb_b_unit = calculate_lightbulb_consumption(
        model_b_impact.energy.value
    )

    streaming_a, streaming_a_unit = calculate_streaming_hours(model_a_impact.gwp.value)
    streaming_b, streaming_b_unit = calculate_streaming_hours(model_b_impact.gwp.value)

    return template.render(
        model_a=model_a,
        model_b=model_b,
        chosen_model=chosen_model,
        model_a_impact=model_a_impact,
        model_b_impact=model_b_impact,
        size_desc=size_desc,
        license_desc=license_desc,
        license_attrs=license_attrs,
        model_a_tokens=model_a_tokens,
        model_b_tokens=model_b_tokens,
        streaming_a=streaming_a,
        streaming_a_unit=streaming_a_unit,
        streaming_b=streaming_b,
        streaming_b_unit=streaming_b_unit,
        lightbulb_a=lightbulb_a,
        lightbulb_a_unit=lightbulb_a_unit,
        lightbulb_b=lightbulb_b,
        lightbulb_b_unit=lightbulb_b_unit,
    )


def determine_choice_badge(reactions):
    your_choice_badge = None
    reactions = [reaction for reaction in reactions if reaction]
    # Case: Only one reaction exists
    if len(reactions) == 1:

        print("reaction")
        print(reactions)
        if reactions[0].get("liked") == True:
            # Assign "a" if the reaction is for the first message
            your_choice_badge = (
                "model-a" if reactions[0].get("index") == 1 else "model-b"
            )

    # Case: Two reactions exist
    elif len(reactions) == 2:
        print("reactions")
        print(reactions)

        # Ensure one reaction is "liked" and the other is different
        if (
            reactions[0].get("liked") == True
            and reactions[0].get("liked") != reactions[1].get("liked")
        ) or (
            reactions[1].get("liked") == True
            and reactions[1].get("liked") != reactions[0].get("liked")
        ):
            # Assign "a" or "b" based on the liked reaction's index
            your_choice_badge = (
                "model-a"
                if reactions[0]["liked"] and reactions[0].get("index") == 1
                else "model-b"
            )

    return your_choice_badge


def get_llm_impact(
    model_extra_info, model_name: str, token_count: int, request_latency: float
) -> dict:
    """Compute or fallback to estimated impact for an LLM."""
    logger = logging.getLogger("languia")
    # TODO: add request latency
    # FIXME: most of the time, won't appear in venv/lib64/python3.11/site-packages/ecologits/data/models.csv, should use compute_llm_impacts instead
    # model_active_parameter_count: ValueOrRange,
    # model_total_parameter_count: ValueOrRange,
    impact = llm_impacts("huggingface_hub", model_name, token_count, request_latency)
    if impact is None:

        logger.debug("impact is None for " + model_name + ", deducing from params")
        if "active_params" in model_extra_info and "total_params" in model_extra_info:
            # TODO: add request latency
            # FIXME: multiply by 1_000_000?
            model_active_parameter_count = int(model_extra_info["active_params"])
            model_total_parameter_count = int(model_extra_info["total_params"])
        else:
            if "params" in model_extra_info:
                # TODO: add request latency
                model_active_parameter_count = int(model_extra_info["params"])
                model_total_parameter_count = int(model_extra_info["params"])
            else:
                logger.error(
                    "impact is None for "
                    + model_name
                    + ", and no params, closed model did not match ecologits list?"
                )
                return None

        # TODO: move to config.py
        electricity_mix_zone = "WOR"
        electricity_mix = electricity_mixes.find_electricity_mix(
            zone=electricity_mix_zone
        )
        if_electricity_mix_adpe = electricity_mix.adpe
        if_electricity_mix_pe = electricity_mix.pe
        if_electricity_mix_gwp = electricity_mix.gwp

        impact = compute_llm_impacts(
            model_active_parameter_count=model_active_parameter_count,
            model_total_parameter_count=model_total_parameter_count,
            output_token_count=token_count,
            if_electricity_mix_adpe=if_electricity_mix_adpe,
            if_electricity_mix_pe=if_electricity_mix_pe,
            if_electricity_mix_gwp=if_electricity_mix_gwp,
        )
    return impact