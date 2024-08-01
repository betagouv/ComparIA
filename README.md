# LANGU:IA

L'arène LANGU:IA consiste à comparer grâce à un dispositif interactif et ludique les réponses générées par différents modèles à une invite donnée. Un utilisateur pose une question en français et obtient des réponses de deux LLM anonymes.

Elle est basée sur [Gradio](https://www.gradio.app/) et [FastChat](https://github.com/lm-sys/FastChat/), le code de l'arène Chatbot Arena par LMSYS.

<https://beta.gouv.fr/startups/languia.html>

## Lancer l'arène

1. Personnaliser le fichier `register-api-endpoint-file.json` avec des clés d'API valide

    - Avec Docker : `cd docker/; docker compose up -d`
    - Sans Docker (mode debug) :  `pip install -r requirements.txt` puis `export LANGUIA_DEBUG=True; uvicorn main:app --reload --timeout-graceful-shutdown 1` ou simplement `uvicorn main:app`
