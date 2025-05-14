from languia.block_arena import (
    # model_dropdown should go in app_state
    app_state,
    chatbot,
    vote_btn,
    conv_a,
    conv_b,
    demo,
    textbox,
    which_model_radio,
    positive_a,
    positive_b,
    negative_a,
    negative_b,
    comments_a,
    comments_b,
)
import traceback
import os
import sentry_sdk

import copy

import openai

from languia.utils import (
    AppState,
    get_ip,
    get_matomo_tracker_from_cookies,
    pick_models,
    to_threeway_chatbot,
    EmptyResponseError,
    second_header_html,
)

from languia.reveal import build_reveal_html, determine_choice_badge

from languia.logs import vote_last_response, sync_reactions, record_conversations

from languia.config import (
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
)

# from fastchat.model.model_adapter import get_conversation_template

from languia.conversation import bot_response, Conversation


import gradio as gr


from languia.config import logger


from languia import config

from custom_components.customchatbot.backend.gradio_customchatbot.customchatbot import ChatMessage


# Register listeners
def register_listeners():

    # Step 0

    # @app_state.change
    def enter_arena(app_state_scoped: AppState):
        # Refresh on picking model? Do it async? Should do it globally and async...

        # TODO: actually check for it
        # tos_accepted = request...
        # if tos_accepted:
        # logger.info(
        #     f"init_arene, session_hash: {request.session_hash}, IP: {get_ip(request)}, cookie: {(get_matomo_tracker_from_cookies(request.cookies))}",
        #     extra={"request": request},
        # )

        # GET PARAMS FROM REQUEST, NO MORE model_dropdown_scoped
        # Already refreshed in enter_arena, but not refreshed if submit_first_prompt accessed directly
        # TODO: replace outage detection with disabling models + use litellm w/ routing and outage detection
        # didnt_reset_prompt = True
        # text = request.kwargs.get("prompt_value", "")
        # mode = request.kwargs.get("mode", "random")
        mode = "random"
        app_state_scoped.mode = mode
        # custom_models_selection = request.kwargs.get("custom_models_selection", [])
        custom_models_selection = []
        app_state_scoped.custom_models_selection = custom_models_selection

        # Check if "Enter" pressed and no text or still awaiting response and return early

        first_model_name, second_model_name = pick_models(mode, custom_models_selection)

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
        return app_state_scoped, conv_a_scoped, conv_b_scoped

    # Step 1

    def add_text(
        app_state_scoped,
        conv_a_scoped: gr.State,
        conv_b_scoped: gr.State,
        text: gr.Textbox,
        request: gr.Request,
        event: gr.EventData,
    ):

        conversations = [conv_a_scoped, conv_b_scoped]

        # Check if "Enter" pressed and no text or still awaiting response and return early
        if text == "":
            raise (gr.Error("Veuillez entrer votre texte.", duration=10))
        if app_state_scoped.awaiting_responses:
            raise (
                gr.Error(
                    message="Veuillez attendre la fin de la réponse des modèles avant de renvoyer une question.",
                    duration=10,
                )
            )

        logger.info(
            f"msg_user: {text}",
            extra={"request": request},
        )

        if len(text) > BLIND_MODE_INPUT_CHAR_LEN_LIMIT:
            logger.info(
                f"Conversation input exceeded character limit ({BLIND_MODE_INPUT_CHAR_LEN_LIMIT} chars). Truncated text: {text[:BLIND_MODE_INPUT_CHAR_LEN_LIMIT]} ",
                extra={"request": request},
            )

        text = text[:BLIND_MODE_INPUT_CHAR_LEN_LIMIT]
        for i in range(config.num_sides):
            conversations[i].messages.append(ChatMessage(role="user", content=text))
        conv_a_scoped = conversations[0]
        conv_b_scoped = conversations[1]
        app_state_scoped.awaiting_responses = True

        # record for questions only dataset and stats on ppl abandoning before generation completion
        record_conversations(app_state_scoped, [conv_a_scoped, conv_b_scoped], request)

        chatbot = to_threeway_chatbot(conversations)
        text = gr.update(visible=True, value="")

        try:
            gen_a = bot_response(
                "a",
                conv_a_scoped,
                request,
                apply_rate_limit=True,
                use_recommended_config=True,
            )
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

                chatbot = to_threeway_chatbot([conv_a_scoped, conv_b_scoped])
                yield [
                    app_state_scoped,
                    conv_a_scoped,
                    conv_b_scoped,
                    chatbot,
                    gr.skip(),
                ]
        except Exception as e:

            conv_a_scoped.messages[-1].error = str(e)
            conv_b_scoped.messages[-1].error = str(e)

            conversations = [conv_a_scoped, conv_b_scoped]
            error_with_endpoint = conversations[i].endpoint.get("api_id")
            error_with_model = conversations[i].model_name

            if os.getenv("SENTRY_DSN"):

                # with sentry_sdk.configure_scope() as scope:
                # Set the fingerprint based on the message content
                # scope.fingerprint = [e]
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

        finally:

            # Got answer at this point
            app_state_scoped.awaiting_responses = False

            record_conversations(
                app_state_scoped, [conv_a_scoped, conv_b_scoped], request
            )

            if not conv_a_scoped.messages[-1].role == "user":
                logger.info(
                    f"response_modele_a ({conv_a_scoped.model_name}): {str(conv_a_scoped.messages[-1].content)}",
                    extra={"request": request},
                )
                logger.info(
                    f"response_modele_b ({conv_b_scoped.model_name}): {str(conv_b_scoped.messages[-1].content)}",
                    extra={"request": request},
                )

            chatbot = to_threeway_chatbot([conv_a_scoped, conv_b_scoped])

            yield [app_state_scoped, conv_a_scoped, conv_b_scoped]

    gr.on(
        triggers=[
            demo.load,
        ],
        fn=enter_arena,
        api_name="select_mode",
        inputs=[app_state],
        outputs=[app_state] + [conv_a] + [conv_b],
        show_progress="hidden",
    )

    gr.on(
        triggers=[textbox.submit],
        inputs=[app_state] + [conv_a] + [conv_b] + [textbox],
        # inputs=[app_state] + [conv_a] + [conv_b],
        # inputs=[app_state] + [conv_a] + [conv_b] + [textbox],
        fn=add_text,
        api_name="submit_response",
        outputs=[app_state] + [conv_a] + [conv_b],
        # scroll_to_output=True,
        show_progress="hidden",
    )

    @chatbot.like(
        inputs=[app_state] + [conv_a] + [conv_b] + [chatbot],
        outputs=[app_state],
        api_name="react",
        show_progress="hidden",
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
        return build_reveal_html(
            conv_a=conv_a_scoped,
            conv_b=conv_b_scoped,
            which_model_radio=which_model_radio_output,
        )

    gr.on(
        triggers=[vote_btn.click],
        fn=vote_preferences,
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
        # outputs=[quiz_modal],
        api_name="vote",
        # scroll_to_output=True,
        show_progress="hidden",
    )
