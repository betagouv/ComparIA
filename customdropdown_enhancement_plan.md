# Plan de migration de la logique des "Suggestions de prompts"

## 1. Préparation du composant Svelte ([`custom_components/customdropdown/frontend/Index.svelte`](custom_components/customdropdown/frontend/Index.svelte:1))
   *   **Définition des données des cartes guidées en JavaScript :**
       *   Dans la section `<script lang="ts">` du fichier [`custom_components/customdropdown/frontend/Index.svelte`](custom_components/customdropdown/frontend/Index.svelte:5), nous allons recréer les données des cartes.
       *   Transposer la variable Python `total_guided_cards_choices` (définie dans [`languia/config.py:251-308`](languia/config.py:251)) en un tableau d'objets JavaScript. Chaque objet contiendra au moins une propriété pour le HTML de la carte (par exemple, `html`) et une pour la valeur du prompt (par exemple, `promptValue` ou `id`).
       *   Faire de même pour `ia_summit_choice` ([`languia/config.py:314-323`](languia/config.py:314)).
       *   Nous allons également implémenter la logique de mélange aléatoire et de sélection d'un sous-ensemble de cartes, ainsi que l'insertion de `ia_summit_choice` au début, directement en JavaScript.
   *   **Création d'un nouveau sous-composant Svelte pour les cartes guidées :**
       *   Créer un nouveau fichier Svelte, par exemple `GuidedPromptSuggestions.svelte`, dans le dossier `custom_components/customdropdown/frontend/shared/`.
       *   Ce composant sera responsable de :
           *   L'affichage du titre "Suggestions de prompts" (actuellement `prompts_suggestions` dans [`languia/block_arena.py:70-73`](languia/block_arena.py:70)).
           *   L'affichage des cartes guidées (actuellement `guided_cards` dans [`languia/block_arena.py:74-80`](languia/block_arena.py:74)). Il recevra la liste des cartes à afficher en tant que `prop`.
           *   L'affichage du bouton "Générer un autre message" (actuellement `shuffle_link` dans [`languia/block_arena.py:81-86`](languia/block_arena.py:81)).
   *   **Logique du bouton "Générer un autre message" dans `GuidedPromptSuggestions.svelte`:**
       *   Ce bouton, une fois cliqué, déclenchera une fonction JavaScript.
       *   Cette fonction prendra la liste complète des cartes (version JavaScript de `total_guided_cards_choices`), la mélangera aléatoirement, sélectionnera un nouveau sous-ensemble, y ajoutera `ia_summit_choice` au début, et mettra à jour l'état du composant pour afficher les nouvelles cartes.
   *   **Intégration de `GuidedPromptSuggestions.svelte` dans `Index.svelte`:**
       *   Importer `GuidedPromptSuggestions.svelte` dans [`custom_components/customdropdown/frontend/Index.svelte`](custom_components/customdropdown/frontend/Index.svelte:1).
       *   L'utiliser dans le template HTML de [`Index.svelte`](custom_components/customdropdown/frontend/Index.svelte:1), en lui passant les données des cartes initiales. Il devrait être positionné logiquement après le champ de texte principal et avant les options de sélection de modèle.
   *   **Gestion de la sélection d'une carte guidée :**
       *   Lorsqu'un utilisateur clique sur une carte dans `GuidedPromptSuggestions.svelte`, le texte du prompt associé à cette carte doit être inséré dans le `TextBox` principal (la variable `prompt_value` ([`custom_components/customdropdown/frontend/Index.svelte:203`](custom_components/customdropdown/frontend/Index.svelte:203)) dans [`Index.svelte`](custom_components/customdropdown/frontend/Index.svelte:1)).
       *   Cela se fera probablement en émettant un événement depuis `GuidedPromptSuggestions.svelte` que [`Index.svelte`](custom_components/customdropdown/frontend/Index.svelte:1) écoutera pour mettre à jour `prompt_value`.

## 2. Modifications dans le backend Python ([`languia/block_arena.py`](languia/block_arena.py:1))
   *   Supprimer les déclarations Gradio pour `prompts_suggestions` ([`languia/block_arena.py:70-73`](languia/block_arena.py:70)), `guided_cards` ([`languia/block_arena.py:74-80`](languia/block_arena.py:74)), et `shuffle_link` ([`languia/block_arena.py:81-86`](languia/block_arena.py:81)).
   *   Supprimer toute logique Python (listeners, etc.) qui était spécifiquement liée à ces trois composants et qui n'est pas déjà gérée par le composant `CustomDropdown` lui-même.

## 3. Modifications dans la configuration Python ([`languia/config.py`](languia/config.py:1))
   *   Puisque la logique et les données des cartes guidées seront recréées en Svelte, les variables Python `total_guided_cards_choices` ([`languia/config.py:251-308`](languia/config.py:251)), `guided_cards_choices` ([`languia/config.py:312`](languia/config.py:312)), et `ia_summit_choice` ([`languia/config.py:314-323`](languia/config.py:314)) ne seront plus nécessaires *pour cette partie du code*. Elles pourront être supprimées de [`languia/config.py`](languia/config.py:1) si elles n'ont pas d'autre usage dans l'application.

## 4. Tests et ajustements
   *   Vérifier l'affichage correct des suggestions de prompts dans le composant `CustomDropdown`.
   *   Tester la fonctionnalité du bouton "Générer un autre message".
   *   S'assurer que le clic sur une carte remplit bien le champ de texte principal.
   *   Vérifier l'absence d'erreurs et la bonne intégration visuelle.

## Diagramme Mermaid illustrant le plan :

```mermaid
graph TD
    subgraph "Avant (Python - languia/block_arena.py)"
        A_config["languia/config.py (total_guided_cards_choices, ia_summit_choice)"] --> B_arena["languia/block_arena.py"]
        B_arena --crée--> C_html["gr.HTML (prompts_suggestions)"]
        B_arena --crée--> D_radiocard["CustomRadioCard (guided_cards)"]
        B_arena --crée--> E_button["gr.Button (shuffle_link)"]
    end

    subgraph "Après (Svelte - custom_components/customdropdown/frontend/)"
        F_index_svelte["Index.svelte"]
        F_index_svelte --contient--> G_js_data["Données des cartes (JS Array)"]
        F_index_svelte --importe et utilise--> H_guided_prompts_svelte["shared/GuidedPromptSuggestions.svelte"]
        
        H_guided_prompts_svelte --affiche--> I_title["Titre 'Suggestions de prompts' (HTML)"]
        H_guided_prompts_svelte --reçoit de F_index_svelte & affiche--> J_cards["Cartes Guidées (rendues via #each)"]
        H_guided_prompts_svelte --affiche--> K_shuffle_btn["Bouton 'Générer un autre message' (HTML)"]
        
        G_js_data --utilisé par--> H_guided_prompts_svelte
        K_shuffle_btn --clic--> L_shuffle_logic["Logique de mélange (JS dans GuidedPromptSuggestions.svelte)"]
        L_shuffle_logic --met à jour l'affichage de--> J_cards
        J_cards --clic sur une carte--> M_event["Événement Svelte (prompt sélectionné)"]
        M_event --capturé par F_index_svelte--> N_update_prompt["Mise à jour de 'prompt_value' dans Index.svelte"]
        N_update_prompt --affecte--> O_textbox["TextBox principal dans Index.svelte"]
    end

    P_py_arena_mod["languia/block_arena.py (modifié)"] --ne contient plus--> C_html
    P_py_arena_mod --ne contient plus--> D_radiocard
    P_py_arena_mod --ne contient plus--> E_button

    Q_py_config_mod["languia/config.py (modifié)"] --peut-être suppression de--> A_config_vars["total_guided_cards_choices, etc."]

    style F_index_svelte fill:#ccf,stroke:#333,stroke-width:2px
    style H_guided_prompts_svelte fill:#ccf,stroke:#333,stroke-width:2px