from languia.block_arena import (
    app_state,
    chatbot,
    vote_btn,
    conv_a,
    conv_b,
    demo,
    # model_dropdown,
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

from gradio import (
    ChatMessage,
)


# Register listeners
def register_listeners():

    # Step 0

    def enter_arena(request: gr.Request):
        # Refresh on picking model? Do it async? Should do it globally and async...

        # TODO: actually check for it
        # tos_accepted = request...
        # if tos_accepted:
        logger.info(
            f"init_arene, session_hash: {request.session_hash}, IP: {get_ip(request)}, cookie: {(get_matomo_tracker_from_cookies(request.cookies))}",
            extra={"request": request},
        )

    # Step 1

    def submit_first_prompt(
        app_state_scoped: AppState,
        request: gr.Request,
        # event: gr.EventData,
    ):
        
        # GET PARAMS FROM REQUEST, NO MORE model_dropdown_scoped
        # Already refreshed in enter_arena, but not refreshed if submit_first_prompt accessed directly
        # TODO: replace outage detection with disabling models + use litellm w/ routing and outage detection
        didnt_reset_prompt = True
        text = request.kwargs.get("prompt_value", "")
        mode = request.kwargs.get("mode", "random")
        app_state_scoped.mode = mode
        custom_models_selection = request.kwargs.get(
            "custom_models_selection", []
        )

        logger.info("chose mode: " + mode, extra={"request": request})
        logger.info(
            "custom_models_selection: " + str(custom_models_selection),
            extra={"request": request},
        )
        # Check if "Enter" pressed and no text or still awaiting response and return early
        if text == "":
            raise (gr.Error("Veuillez entrer votre texte.", duration=10))

        first_model_name, second_model_name = pick_models(
            mode, custom_models_selection
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

        if len(text) > BLIND_MODE_INPUT_CHAR_LEN_LIMIT:
            logger.info(
                f"Conversation input exceeded character limit ({BLIND_MODE_INPUT_CHAR_LEN_LIMIT} chars). Truncated text: {text[:BLIND_MODE_INPUT_CHAR_LEN_LIMIT]} ",
                extra={"request": request},
            )

        text = text[:BLIND_MODE_INPUT_CHAR_LEN_LIMIT]

        # Could be added in Converstation.__init__?
        conv_a_scoped.messages.append(ChatMessage(role="user", content=text))
        conv_b_scoped.messages.append(ChatMessage(role="user", content=text))
        logger.info(
            f"selection_modeles: {first_model_name}, {second_model_name}",
            extra={"request": request},
        )

        logger.info(
            f"conv_pair_id: {conv_a_scoped.conv_id}-{conv_b_scoped.conv_id}",
            extra={"request": request},
        )

        logger.info(
            f"msg_user: {text}",
            extra={"request": request},
        )

        # record for questions only dataset and stats on ppl abandoning before generation completion
        record_conversations(app_state_scoped, [conv_a_scoped, conv_b_scoped], request)
        chatbot = to_threeway_chatbot([conv_a_scoped, conv_b_scoped])
        banner = second_header_html(1, mode)

        text = gr.update(visible=True)
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

                chatbot = to_threeway_chatbot([conv_a_scoped, conv_b_scoped])
                # yield [
                #     app_state_scoped,
                #     conv_a_scoped,
                #     conv_b_scoped,
                #     chatbot,
                #     gr.skip(),
                # ]
                # TODO: refacto to make a first yield for elements then only for conv...?
                if didnt_reset_prompt:
                    new_textbox = gr.update(
                        value="",
                        placeholder="Continuer à discuter avec les deux modèles d'IA",
                    )
                    didnt_reset_prompt = False
                else:
                    new_textbox = gr.skip()
                yield [
                    app_state_scoped,
                    # 2 conversations
                    conv_a_scoped,
                    conv_b_scoped,
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

            conv_a_scoped.messages[-1].error = str(e)
            conv_b_scoped.messages[-1].error = str(e)

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

            chatbot = to_threeway_chatbot([conv_a_scoped, conv_b_scoped])

            yield [
                app_state_scoped,
                # 2 conversations
                conv_a_scoped,
                conv_b_scoped,
                # 1 chatbot
                chatbot,
                text,
                banner,
                # textbox
                gr.skip(),
                # mode_screen
                gr.update(visible=False),
                # chat_area
                gr.update(visible=True),
                # send_btn
                gr.update(interactive=False),
                # conclude_btn
                gr.update(visible=True, interactive=False),
                # send_area
                gr.update(visible=True),
            ]

    def add_text(
        app_state_scoped,
        conv_a_scoped: gr.State,
        conv_b_scoped: gr.State,
        text: gr.Text,
        request: gr.Request,
        event: gr.EventData,
    ):

        # if retry, resend last user errored message
        # TODO: check if it's a retry event more robustly, with listener specifically on Event.retry
        if event._data is not None:
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
            else:
                raise gr.Error(
                    message="Il n'est pas possible de réessayer, veuillez recharger la page.",
                    duration=10,
                )

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
        fn=submit_first_prompt,
        api_name="submit_first_prompt",
        inputs=[app_state],
        outputs=[app_state]
        + [conv_a]
        + [conv_b],
        show_progress="hidden",
    )

    gr.on(
        fn=add_text,
        api_name="submit_response",
        inputs=[app_state] + [conv_a] + [conv_b],
        outputs=[app_state] + [conv_a] + [conv_b],
        # scroll_to_output=True,
        show_progress="hidden",
    )
    

    @chatbot.like(
        inputs=[app_state] + [conv_a] + [conv_b],
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
            # + [which_model_radio]
            # + [positive_a]
            # + [positive_b]
            # + [negative_a]
            # + [negative_b]
            # + [comments_a]
            # + [comments_b]
        ),
        outputs=[
        ],
        # outputs=[quiz_modal],
        api_name="vote",
        # scroll_to_output=True,
        show_progress="hidden",
    )