<br>
<p align="center">
  <a href="https://comparia.beta.gouv.fr/">
  <img src="https://github.com/user-attachments/assets/bd071ffd-1253-486d-ad18-9f5b371788b0" width=300px alt="compar:IA logo" />  </a>
</p>


<h2 align="center" >Comparateur d’IA conversationnelles</h3>
<p align="center">Compar:IA est un outil permettant de comparer à l’aveugle différents modèles d'IA conversationnelle pour sensibiliser aux enjeux de l'IA générative (biais, impact environmental) et constituer des jeux de données de préférence en français.</p>

<p align="center"><a href="https://comparia.beta.gouv.fr/">🌐 comparia.beta.gouv.fr</a> · <a href="https://www.comparia.beta.gouv.fr/a-propos">📚 À propos</a> · <a href="https://beta.gouv.fr/startups/languia.html">🚀 Description de la startup d'Etat</a><p>
<div align="center">
  <a href="https://comparia.beta.gouv.fr/" 
     aria-label="Cliquez pour se rendre sur la plateforme hébergée"
     title="Capture d'écran du comparateur">
    <img 
      src="https://github.com/user-attachments/assets/6c8257fc-a2e5-4ee1-8052-dbf14a0419ea" 
      alt="Aperçu du comparateur" 
      width="800"
    />
  </a>
</div>
<div align="center">
  <sub>
    <i>Cliquez sur l'image ci-dessus pour consulter le site (s'ouvre dans un nouvel onglet)</i>
  </sub>
</div>

<br>

Le comparateur est basé sur [Gradio](https://www.gradio.app/) et [FastChat](https://github.com/lm-sys/FastChat/), le code de l'arène Chatbot Arena par LMSYS.



## Lancer l'arène

1. Personnaliser le fichier `register-api-endpoint-file.json` avec des clés d'API valide

### Avec Docker

`cd docker/; docker compose up -d`

### Sans Docker

```bash
pip install -r requirements.txt
cd custom_components/frinput
gradio cc install;gradio cc build --no-generate-docs
cd ../../custom_components/customradiocard
gradio cc install;gradio cc build --no-generate-docs
cd ../..
```
puis `export LANGUIA_DEBUG=True; uvicorn main:app --reload --timeout-graceful-shutdown 1` ou simplement `uvicorn main:app`
