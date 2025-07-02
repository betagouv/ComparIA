import gradio as gr

import traceback
import os
import sentry_sdk

import copy

from languia.utils import AppState, pick_models

from languia.config import (
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    models_extra_info,
    unavailable_models
)

from languia.logs import vote_last_response, sync_reactions, record_conversations

from languia.conversation import bot_response, Conversation

from languia.config import logger


from custom_components.customchatbot.backend.gradio_customchatbot.customchatbot import (
    ChatMessage,
)


with gr.Blocks(
    title="Discussion - compar:IA, le comparateur d'IA conversationnelles",
    analytics_enabled=False,
) as demo:

    app_state = gr.State(value=AppState())

    conv_a = gr.State()
    conv_b = gr.State()
    # model_selectors = [None] * num_sides

    mode_dropdown = gr.Dropdown(
        # ignored, hardcoded in custom component
        choices=["random", "big-vs-small", "small-models", "reasoning", "custom"],
    )
    models_selection = gr.CheckboxGroup(choices=models_extra_info)

    textbox = gr.Textbox(
        elem_id="main-textbox",
        show_label=False,
        lines=1,
        placeholder="Continuer à discuter avec les deux modèles d'IA",
        max_lines=7,
        elem_classes="w-full",
        container=True,
        autofocus=True,
    )
    send_btn = gr.Button(
        value="Envoyer",
    )

    chatbot1 = gr.Chatbot(type="messages")
    chatbot2 = gr.Chatbot(type="messages")

    retry_btn = gr.Button("Retry")

    which_model_radio = gr.Radio(
        elem_id="vote-cards",
        choices=[
            (
                """Modèle A""",
                "model-a",
            ),
            (
                """Les deux se valent""",
                "both-equal",
            ),
            (
                """Modèle B""",
                "model-b",
            ),
        ],
        show_label=False,
    )

    positive_a = gr.CheckboxGroup(
        elem_classes="thumb-up-icon flex-important checkboxes fr-mb-2w",
        show_label=False,
        choices=[
            ("Utiles", "useful"),
            ("Complètes", "complete"),
            ("Créatives", "creative"),
            ("Mise en forme claire", "clear-formatting"),
        ],
    )

    negative_a = gr.CheckboxGroup(
        elem_classes="thumb-down-icon flex-important checkboxes fr-mb-2w",
        show_label=False,
        choices=[
            ("Incorrectes", "incorrect"),
            ("Superficielles", "superficial"),
            ("Instructions non respectées", "instructions-not-followed"),
        ],
    )

    comments_a = gr.Textbox(
        show_label=False,
        visible=False,
        lines=3,
        placeholder="Les réponses du modèle A sont...",
    )

    positive_b = gr.CheckboxGroup(
        elem_classes="thumb-up-icon flex-important checkboxes fr-mb-2w",
        show_label=False,
        choices=[
            ("Utiles", "useful"),
            ("Complètes", "complete"),
            ("Créatives", "creative"),
            ("Mise en forme claire", "clear-formatting"),
        ],
    )

    negative_b = gr.CheckboxGroup(
        elem_classes="thumb-down-icon flex-important checkboxes fr-mb-2w",
        show_label=False,
        choices=[
            ("Incorrectes", "incorrect"),
            ("Superficielles", "superficial"),
            ("Instructions non respectées", "instructions-not-followed"),
        ],
    )
    comments_b = gr.Textbox(
        show_label=False,
        visible=False,
        lines=3,
        placeholder="Les réponses du modèle B sont...",
    )
    comments_link = gr.Button(elem_classes="link fr-mt-1w", value="Ajouter des détails")

    conclude_btn = gr.Button(
        size="lg",
        value="Passer à la révélation des modèles",
        elem_classes="fr-col-12 fr-col-md-5 purple-btn fr-mt-1w",
        visible=False,
        interactive=False,
    )

    supervote_send_btn = gr.Button(
        elem_classes="purple-btn fr-mx-auto fr-col-10 fr-col-md-4",
        value="Passer à la révélation des modèles",
        size="lg",
        interactive=False,
    )

    # Register listeners

    # FIXME: conv_a_scoped and conv_b_scoped as input??
    @mode_dropdown.select(
        inputs=[app_state] + [mode_dropdown] + [models_selection],
        outputs=[app_state] + [conv_a] + [conv_b],
        api_name="draw_models",
    )
    @models_selection.select(
        inputs=[app_state] + [mode_dropdown] + [models_selection],
        outputs=[app_state] + [conv_a] + [conv_b],
        api_name="draw_models",
    )
    def draw_models(
        app_state_scoped: AppState,
        request: gr.Request,
        mode: gr.Radio = "random",
        custom_models_selection: gr.CheckboxGroup = [],
    ):
        app_state_scoped.mode = mode

        logger.info("chose mode: " + mode, extra={"request": request})
        logger.info(
            "custom_models_selection: " + str(custom_models_selection),
            extra={"request": request},
        )

        first_model_name, second_model_name = pick_models(
            mode, custom_models_selection, unavailable_models=unavailable_models
        )

        # Important: to avoid sharing object references between Gradio sessions
        conv_a_scoped = copy.deepcopy(
            Conversation(
                model_name=first_model_name,
            )
        )
        conv_b_scoped = copy.deepcopy(
            Conversation(
                model_name=second_model_name,
            )
        )

        logger.info(
            f"selection_modeles: {first_model_name}, {second_model_name}",
            extra={"request": request},
        )
        return app_state_scoped, conv_a_scoped, conv_b_scoped

    @send_btn.click(
        api_name="add_text",
        inputs=[app_state] + [conv_a] + [conv_b] + [textbox],
        outputs=[app_state] + [conv_a] + [conv_b] + [chatbot1] + [chatbot2],
    )
    @textbox.submit(
        api_name="add_text",
        inputs=[app_state] + [conv_a] + [conv_b] + [textbox],
        outputs=[app_state] + [conv_a] + [conv_b] + [chatbot1] + [chatbot2],
    )
    def add_text(
        app_state_scoped,
        conv_a_scoped: gr.State,
        conv_b_scoped: gr.State,
        text: gr.Text,
        request: gr.Request,
        event: gr.EventData,
    ):
        # Check if "Enter" pressed and no text or still awaiting response and return early
        if text == "":
            raise (gr.Error("Veuillez entrer votre texte.", duration=10))

        if len(text) > BLIND_MODE_INPUT_CHAR_LEN_LIMIT:
            logger.info(
                f"Conversation input exceeded character limit ({BLIND_MODE_INPUT_CHAR_LEN_LIMIT} chars). Truncated text: {text[:BLIND_MODE_INPUT_CHAR_LEN_LIMIT]} ",
                extra={"request": request},
            )

            text = text[:BLIND_MODE_INPUT_CHAR_LEN_LIMIT]

        conv_a_scoped.messages.append(ChatMessage(role="user", content=text))
        conv_b_scoped.messages.append(ChatMessage(role="user", content=text))
        logger.info(
            f"conv_pair_id: {conv_a_scoped.conv_id}-{conv_b_scoped.conv_id}",
            extra={"request": request},
        )

        logger.info(
            f"msg_user: {text}",
            extra={"request": request},
        )

        # record for stats on ppl abandoning before generation completion
        record_conversations(app_state_scoped, [conv_a_scoped, conv_b_scoped], request)

        app_state_scoped.awaiting_responses = True

        try:
            i = 0
            gen_a = bot_response(
                "a",
                conv_a_scoped,
                request,
                apply_rate_limit=True,
                use_recommended_config=True,
            )
            i = 1
            gen_b = bot_response(
                "b",
                conv_b_scoped,
                request,
                apply_rate_limit=True,
                use_recommended_config=True,
            )
            while True:
                try:
                    i = 0
                    response_a = next(gen_a)
                    conv_a_scoped = response_a

                except StopIteration:
                    response_a = None
                try:
                    i = 1
                    response_b = next(gen_b)
                    conv_b_scoped = response_b
                except StopIteration:
                    response_b = None
                if response_a is None and response_b is None:
                    break

                yield [
                    app_state_scoped,
                    # 2 conversations
                    conv_a_scoped,
                    conv_b_scoped,
                    conv_a_scoped.messages,
                    conv_b_scoped.messages,
                ]

        except Exception as e:

            conversations = [conv_a_scoped, conv_b_scoped]
            error_with_endpoint = conversations[i].endpoint.get("api_id")
            error_with_model = conversations[i].model_name

            if os.getenv("SENTRY_DSN"):
                sentry_sdk.capture_exception(e)

            logger.exception(
                f"erreur_modele: {error_with_model}, {error_with_endpoint}, '{e}'\n{traceback.format_exc()}",
                extra={
                    "request": request,
                    "error": str(e),
                    "stacktrace": traceback.format_exc(),
                },
                exc_info=True,
            )
            if i == 0:
                conv_error = conv_a_scoped
            else:
                conv_error = conv_b_scoped

            def only_has_one_user_msg(messages):
                #  reroll only if generation hasn't started
                user_msgs_count = 0
                for msg in messages:
                    if msg.role == "user":
                        user_msgs_count += 1
                        if user_msgs_count > 1:
                            return False
                if user_msgs_count == 1:
                    return True
                else:
                    return False

            if only_has_one_user_msg(conv_error.messages):
                if app_state_scoped.mode == "custom":
                    gr.Warning(
                        duration=20,
                        title="",
                        message="""<div class="visible fr-p-2w">Le comparateur n'a pas pu piocher parmi les modèles sélectionnés car ils ne sont temporairement pas disponibles. Si vous réessayez, le comparateur piochera parmi d'autres modèles.</div>""",
                    )

                # FIXME: only repick and regenerate the conv_error
                model_left, model_right = pick_models(
                    app_state_scoped.mode,
                    # Doesn't make sense to keep custom model options here
                    # FIXME: if error with model wasn't the one chosen (case where you select only one model) just reroll the other one
                    [],
                    # temporarily exclude the buggy model here
                    unavailable_models + [error_with_model],
                )
                logger.info(
                    f"reinitializing convs w/ two new models: {model_left} and {model_right}",
                    extra={"request": request},
                )
                conv_a_scoped = copy.deepcopy(Conversation(model_name=model_left))
                conv_b_scoped = copy.deepcopy(Conversation(model_name=model_right))
                logger.info(
                    f"new conv ids: {conv_a_scoped.conv_id} and {conv_b_scoped.conv_id}",
                    extra={"request": request},
                )

                # Don't reuse same conversation ID
                conv_a_scoped.messages.append(ChatMessage(role="user", content=text))
                conv_b_scoped.messages.append(
                    ChatMessage(role="user", content=text, error=str(e))
                )
        finally:
            # Got answer at this point (or error?)
            app_state_scoped.awaiting_responses = False

            record_conversations(
                app_state_scoped, [conv_a_scoped, conv_b_scoped], request
            )

            if conv_a_scoped.messages[-1].role != "user":
                logger.info(
                    f"response_modele_a ({conv_a_scoped.model_name}): {str(conv_a_scoped.messages[-1].content)}",
                    extra={"request": request},
                )
            if conv_b_scoped.messages[-1].role != "user":
                logger.info(
                    f"response_modele_b ({conv_b_scoped.model_name}): {str(conv_b_scoped.messages[-1].content)}",
                    extra={"request": request},
                )

            conversations = [conv_a_scoped, conv_b_scoped]
            record_conversations(
                app_state_scoped, [conv_a_scoped, conv_b_scoped], request
            )

            # chatbot = [conv_a_scoped.messages, conv_b_scoped.messages]
            # chatbot = conversations
            return [
                app_state_scoped,
                # 2 conversations
                conv_a_scoped,
                conv_b_scoped,
                # chatbot,
                # chatbot1,
                # chatbot2
                conv_a_scoped.messages,
                conv_b_scoped.messages
            ]

    @retry_btn.click(
        api_name="retry",
        inputs=[app_state] + [conv_a] + [conv_b],
        outputs=[app_state] + [conv_a] + [conv_b] + [chatbot1] + [chatbot2],
    )
    def retry(
        app_state_scoped,
        conv_a_scoped,
        conv_b_scoped,
        request: gr.Request,
        event: gr.EventData,
    ):
        # if retry, resend last user errored message
        # TODO: check if it's a retry event more robustly, with listener specifically on Event.retry
        app_state_scoped.awaiting_responses = False

        if (
            conv_a_scoped.messages[-1].role == "assistant"
            and conv_b_scoped.messages[-1].role == "assistant"
        ):
            conv_a_scoped.messages = conv_a_scoped.messages[:-1]
            conv_b_scoped.messages = conv_b_scoped.messages[:-1]

        if (
            conv_a_scoped.messages[-1].role == "user"
            and conv_b_scoped.messages[-1].role == "user"
        ):
            text = conv_a_scoped.messages[-1].content
            conv_a_scoped.messages = conv_a_scoped.messages[:-1]
            conv_b_scoped.messages = conv_b_scoped.messages[:-1]
            return add_text(
                app_state_scoped,
                conv_a_scoped,
                conv_b_scoped,
                text,
                request=request,
                event=event,
            )

        else:
            raise gr.Error(
                message="Il n'est pas possible de réessayer, veuillez recharger la page.",
                duration=10,
            )
    # FIXME: hardening, only show model name to frontend if this function passes?
    # def is_vote_needed(
    #     app_state_scoped,request: gr.Request
    # ):

    #     for reaction in app_state_scoped.reactions:
    #         if reaction:
    #             if reaction["liked"] != None:
    #                 print("meaningful_reaction")
    #                 logger.debug(reaction)
    #                 return False
    #     # If no break found
    #     else:
    #         logger.debug("no meaningful reaction found, inflicting vote screen")
    #         print(
    #             "ecran_vote",
    #             extra={"request": request},
    #         )
    #         return True

    @chatbot1.like(
        inputs=[app_state] + [conv_a] + [conv_b] + [chatbot1],
        outputs=[app_state],
        api_name="chatbot1_react",
    )
    @chatbot2.like(
        inputs=[app_state] + [conv_a] + [conv_b] + [chatbot2],
        outputs=[app_state],
        api_name="chatbot2_react",
    )
    def record_like(
        app_state_scoped,
        conv_a_scoped,
        conv_b_scoped,
        chatbot,
        event: gr.EventData,
        request: gr.Request,
    ):
        # A comment is always on an existing reaction, but the like event on commenting doesn't give you the full reaction, it could though
        # TODO: or just create another event type like "Event.react"
        if "comment" in event._data:
            app_state_scoped.reactions[event._data["index"]]["comment"] = event._data[
                "comment"
            ]
        else:
            while len(app_state_scoped.reactions) <= event._data["index"]:
                app_state_scoped.reactions.extend([None])
            app_state_scoped.reactions[event._data["index"]] = event._data

        sync_reactions(
            conv_a_scoped,
            conv_b_scoped,
            chatbot,
            app_state_scoped.reactions,
            request=request,
        )
        return app_state_scoped

    @supervote_send_btn.click(
        inputs=(
            [app_state]
            + [conv_a]
            + [conv_b]
            + [which_model_radio]
            + [positive_a]
            + [positive_b]
            + [negative_a]
            + [negative_b]
            + [comments_a]
            + [comments_b]
        ),
        outputs=[],
        api_name="chatbot_vote",
    )
    def vote_preferences(
        app_state_scoped,
        conv_a_scoped,
        conv_b_scoped,
        which_model_radio_output,
        positive_a_output,
        positive_b_output,
        negative_a_output,
        negative_b_output,
        comments_a_output,
        comments_b_output,
        request: gr.Request,
    ):
        details = {
            "prefs_a": [*positive_a_output, *negative_a_output],
            "prefs_b": [*positive_b_output, *negative_b_output],
            "comments_a": str(comments_a_output),
            "comments_b": str(comments_b_output),
        }
        if hasattr(app_state_scoped, "category"):
            category = app_state_scoped.category
        else:
            category = None

        vote_last_response(
            [conv_a_scoped, conv_b_scoped],
            which_model_radio_output,
            category,
            details,
            request,
        )
        return True


# Launch the Gradio app directly
if __name__ == "__main__":
    demo.launch(
        root_path="/arene",
        server_name="0.0.0.0",
        server_port=7860,  # Default Gradio port
        share=False,  # Set to True if you want to create a shareable link
    )
