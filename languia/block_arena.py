"""
ComparIA Arena UI Definition and Layout.

Main Gradio interface for comparing two LLM models side-by-side.
This module defines the complete UI structure including:
- Model selection dropdown
- Chat interface with custom components
- Voting/preference UI
- Reveal screen for model names and statistics

The actual event handlers are registered in listeners.py which connects
these UI components to backend functionality.

Architecture:
- gr.Blocks() creates the main interface container
- Custom Gradio components: CustomDropdown, CustomChatbot, CustomRadioCard
- State management through gr.State() for conversations and app state
- Event listeners registered via register_listeners() from listeners.py
- Responsive layout with DSFR CSS framework integration

Main Components:
1. Model Selector (CustomDropdown)
   - Modes: random, big-vs-small, small-models, custom
2. Chat Area (CustomChatbot)
   - Likeable interface for individual message reactions
   - Textarea for continued conversation
   - "Conclude" button to proceed to voting
3. Vote Area (supervote_area)
   - Radio selection: Model A / Both equal / Model B
   - Preference checkboxes (useful, complete, creative, etc.)
   - Comment textboxes
4. Reveal Screen
   - Model names and statistics revealed after voting
"""

import gradio as gr

# from gradio_modal import Modal

from languia.utils import (
    AppState,
)


from languia.custom_components.customchatbot import CustomChatbot
from languia.custom_components.customdropdown import CustomDropdown
from languia.custom_components.customradiocard import CustomRadioCard

from languia import config

with gr.Blocks(
    title="Discussion - compar:IA, le comparateur d'IA conversationnelles",
    analytics_enabled=False,
) as demo:
    """
    Main Gradio Blocks interface.

    Components exposed here are referenced by listeners.py to wire up event handlers.
    All state is managed through gr.State() objects which persist across requests.
    """

    # Application state object holding user preferences, selected mode, category, etc.
    app_state = gr.State(value=AppState())

    locale = gr.Text()

    conv_a = gr.State()
    conv_b = gr.State()
    header = gr.HTML("", elem_id="header-html")

    # Model selection UI (custom component with built-in UI logic)
    # Provides 4 modes: random, big-vs-small, small-models, custom
    # The CustomDropdown component handles rendering and manages selected models
    model_dropdown = CustomDropdown(
        # models=config.models,
        # Note: choices parameter is ignored, hardcoded in custom component
        choices=["random", "big-vs-small", "small-models", "custom"],
        interactive=True,
    )

    # Chat Area: Main conversation display
    with gr.Group() as chat_area:

        # Main chat display showing merged/alternating responses from both models
        # CustomChatbot is a modified Gradio Chatbot with reaction UI built-in
        chatbot = CustomChatbot(
            likeable=True,  # Enables like/dislike buttons on each message
        )

        # Hidden JSON state for tracking user reactions to individual messages
        # Populated by the CustomChatbot component as user interacts
        reaction_json = gr.JSON(visible=False)

        # Vote Area: Model preference voting interface
        # Shown when user clicks "Conclude" button (after chat)
        with gr.Column() as vote_area:

            # Radio selection for which model user prefers
            # CustomRadioCard shows as visual cards instead of traditional radio
            which_model_radio = CustomRadioCard(
                choices=[
                    ("Modèle A", "model-a"),
                    ("Les deux se valent", "both-equal"),
                    ("Modèle B", "model-b"),
                ],
            )

            positive_a = gr.CheckboxGroup(
                choices=[
                    ("Utiles", "useful"),
                    ("Complètes", "complete"),
                    ("Créatives", "creative"),
                    ("Mise en forme claire", "clear-formatting"),
                ],
            )

            negative_a = gr.CheckboxGroup(
                choices=[
                    ("Incorrectes", "incorrect"),
                    ("Superficielles", "superficial"),
                    (
                        "Instructions non respectées",
                        "instructions-not-followed",
                    ),
                ],
            )

            comments_a = gr.Textbox()

            positive_b = gr.CheckboxGroup(
                choices=[
                    ("Utiles", "useful"),
                    ("Complètes", "complete"),
                    ("Créatives", "creative"),
                    ("Mise en forme claire", "clear-formatting"),
                ],
            )

            negative_b = gr.CheckboxGroup(
                choices=[
                    ("Incorrectes", "incorrect"),
                    ("Superficielles", "superficial"),
                    (
                        "Instructions non respectées",
                        "instructions-not-followed",
                    ),
                ],
            )
            comments_b = gr.Textbox()

    # Send Area: Text input and control buttons
    # Shown when chat area is visible (after models selected)
    with gr.Column() as send_area:

        # Main text input for user prompts/follow-ups
        textbox = gr.Textbox()

        # Send button - disabled until models are selected and text entered
        send_btn = gr.Button()

        # Conclude button: moves to voting screen
        conclude_btn = gr.Button()

    with gr.Column(
        elem_classes="fr-container--fluid fr-py-2w fr-grid-row",
        elem_id="buttons-footer",
        visible=False,
    ) as buttons_footer:

        supervote_send_btn = gr.Button(
            elem_classes="purple-btn fr-mx-auto fr-col-10 fr-col-md-4",
            value="Passer à la révélation des modèles",
            size="lg",
            interactive=False,
        )

    with gr.Column(
        elem_id="reveal-screen", visible=False, elem_classes="min-h-screen fr-pt-4w"
    ) as reveal_screen:

        results_area = gr.HTML()

        footer_area = gr.HTML()

    available_models = gr.JSON(visible=False)
    reveal_data = gr.JSON(visible=False)

    from languia.listeners import register_listeners

    register_listeners()
