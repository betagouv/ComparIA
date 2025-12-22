"""
Gradio event listeners for the ComparIA arena.

This module registers all UI event handlers (button clicks, text changes, etc.)
and orchestrates the flow of conversation, voting, and data persistence.

Key flows:
1. User enters arena → models loaded
2. User enters prompt → models selected and called
3. User votes → data persisted
4. User reacts → reactions stored
"""

import copy
import logging
import os
import traceback
from typing import List

import gradio as gr
import requests
import sentry_sdk

from backend.config import BLIND_MODE_INPUT_CHAR_LEN_LIMIT, settings
from backend.language_models.data import get_models
from backend.session import (
    increment_input_chars,
    is_ratelimited,
    r,
    redis_host,
    retrieve_cohorts_redis,
)
from backend.utils.user import get_ip
from languia.block_arena import (  # UI state components; first_textbox,
    CustomDropdown,
    app_state,
    available_models,
    buttons_footer,
    chat_area,
    chatbot,
    comments_a,
    comments_b,
    conclude_btn,
    conv_a,
    conv_b,
    demo,
    header,
    locale,
    model_dropdown,
    negative_a,
    negative_b,
    positive_a,
    positive_b,
    reaction_json,
    reveal_data,
    send_area,
    send_btn,
    supervote_send_btn,
    textbox,
    vote_area,
    which_model_radio,
)
from languia.config import unavailable_models
from languia.conversation import Conversation, bot_response
from languia.custom_components.customchatbot import ChatMessage
from languia.logs import record_conversations, sync_reactions, vote_last_response
from languia.reveal import build_reveal_dict, determine_choice_badge
from languia.utils import (
    AppState,
    get_chosen_model,
    get_matomo_tracker_from_cookies,
    to_threeway_chatbot,
)

logger = logging.getLogger("languia")

m = get_models()
models = m.enabled
pricey_models = m.pricey_models


def register_listeners():
    """
    Register all Gradio event listeners for the ComparIA arena.

    This function binds UI events to handler functions that orchestrate:
    - User input processing
    - Model selection and API calls
    - Vote and reaction recording
    - Conversation persistence
    """

    # ==================== STEP 0: Arena Entry ====================
    # When page loads, display available models

    def enter_arena(request: gr.Request):
        """
        Entry point when user visits the arena.

        Logs session initialization and returns available models list.

        Args:
            request: Gradio request with session info

        Returns:
            dict: Available models from config
        """
        # TODO: actually check for Terms of Service acceptance
        # tos_accepted = request...
        # if tos_accepted:
        logger.info(
            f"init_arene, session_hash: {request.session_hash}, IP: {get_ip(request)}, cookie: {(get_matomo_tracker_from_cookies(request.cookies))}",
            extra={"request": request},
        )
        return models

    gr.on(
        triggers=[demo.load],  # Triggered when page loads
        fn=enter_arena,
        inputs=None,
        outputs=available_models,
        api_name="enter_arena",
        show_progress="hidden",
    )

    # ==================== STEP 1: User Input ====================
    # Handle text input changes and model selection

    @textbox.change(
        inputs=[app_state, textbox],
        outputs=[send_btn],
        api_name=False,
        show_progress="hidden",
    )
    def change_send_btn_state(app_state_scoped, textbox):
        """
        Enable/disable send button based on input state.

        Args:
            app_state_scoped: Current app state
            textbox: User's text input

        Returns:
            gr.update: Updated button state (interactive=True/False)
        """
        # Disable if no text or waiting for responses
        if textbox == "" or (
            hasattr(app_state_scoped, "awaiting_responses")
            and app_state_scoped.awaiting_responses
        ):
            return gr.update(interactive=False)
        else:
            return gr.update(interactive=True)

    def add_first_text(
        app_state_scoped: AppState,
        model_dropdown_scoped: CustomDropdown,
        locale: gr.Text,
        request: gr.Request,
        # event: gr.EventData,
    ):
        """
        Process user's first message and initiate model comparison.

        This is the main handler for the send button click. It:
        1. Extracts user input and mode selection
        2. Selects two models to compare
        3. Calls both models in parallel
        4. Handles rate limiting and validation

        Args:
            app_state_scoped: Current app state
            model_dropdown_scoped: User's model selection (mode + custom choices)
            locale: Country portal (FR, DA, etc.)
            request: Gradio request for logging

        Returns:
            tuple: Updated UI components (conversations, chatbot, app_state, etc.)

        Raises:
            gr.Error: If input validation fails or rate limiting triggered
        """
        didnt_reset_prompt = True
        # Extract user input and model selection preferences
        text = model_dropdown_scoped.get("prompt_value", "")
        mode = model_dropdown_scoped.get("mode", "random")
        app_state_scoped.mode = mode
        custom_models_selection = model_dropdown_scoped.get(
            "custom_models_selection", []
        )
        logger.info(
            f"locale: {locale}",
            extra={"request": request},
        )

        logger.info("chose mode: " + mode, extra={"request": request})
        logger.info(
            "custom_models_selection: " + str(custom_models_selection),
            extra={"request": request},
        )
        # Validate user entered text
        if text == "":
            raise (gr.Error("Veuillez entrer votre texte.", duration=10))

        # Select two models based on mode (random, big-vs-small, reasoning, etc.)
        first_model_name, second_model_name = m.pick_two(
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

        ip = get_ip(request)

        if redis_host and is_ratelimited(ip):
            logger.error(
                f"Too much text submitted to pricey models for ip {ip}",
                extra={"request": request},
            )
            raise gr.Error(
                f"Vous avez trop sollicité les modèles parmi les plus onéreux, veuillez réessayer dans quelques heures. Vous pouvez toujours solliciter des modèles plus petits."
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

        # record for questions only dataset and stats on ppl abandoning before generation completion + add locale info
        # Check if session has cohorts using direct Redis get

        cohorts_comma_separated = retrieve_cohorts_redis(request.session_hash)

        logger.info(
            f"cohorts_comma_separated: {cohorts_comma_separated}",
            extra={"request": request},
        )

        record_conversations(
            app_state_scoped,
            [conv_a_scoped, conv_b_scoped],
            request,
            locale,
            cohorts_comma_separated=cohorts_comma_separated,
        )
        chatbot = to_threeway_chatbot([conv_a_scoped, conv_b_scoped])

        app_state_scoped.awaiting_responses = True

        try:
            i = 0
            gen_a = bot_response("a", conv_a_scoped, request)
            i = 1
            gen_b = bot_response("b", conv_b_scoped, request)
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
                    # 1 chatbot
                    chatbot,
                    text,
                    # banner
                    gr.skip(),
                    # textbox
                    new_textbox,
                    # custom_dropdown
                    gr.update(visible=False),
                    # chat_area
                    gr.update(visible=True),
                    # send_btn
                    gr.update(interactive=False),
                    # conclude_btn
                    gr.update(visible=True, interactive=False),
                    gr.update(visible=True),
                ]
            if first_model_name in pricey_models:
                increment_input_chars(ip, len(text))
            if second_model_name in pricey_models:
                increment_input_chars(ip, len(text))
        except Exception as e:

            conv_a_scoped.messages[-1].error = str(e)
            conv_b_scoped.messages[-1].error = str(e)

            conversations = [conv_a_scoped, conv_b_scoped]
            error_with_endpoint = conversations[i].endpoint.get("api_id")
            error_with_model = conversations[i].model_name

            if os.getenv("SENTRY_DSN"):
                # TODO: only capture model name to sort more easily in sentry

                sentry_sdk.capture_exception(e)

            error_reason = (
                f"error_first_text: {error_with_model}, {error_with_endpoint}, {e}"
            )
            print(error_reason)
            try:
                requests.post(
                    f"{settings.LANGUIA_CONTROLLER_URL}/models/{error_with_model}/error",
                    json={"error": error_reason},
                    timeout=1,
                )
            except:
                pass

            logger.exception(
                error_reason,
                extra={
                    "request": request,
                    "error": str(e),
                    "stacktrace": traceback.format_exc(),
                },
                exc_info=True,
            )
            # If it's the first message in conversation, re-roll
            if i == 0:
                conv_error = conv_a_scoped
            else:
                conv_error = conv_b_scoped

            if len(conv_error.messages) == 1 or (
                len(conv_error.messages) == 2
                and conv_error.messages[0].role == "system"
            ):
                if len(conv_error.messages) == 1:
                    original_user_prompt = conv_error.messages[0].content
                else:
                    original_user_prompt = conv_error.messages[1].content

                if app_state_scoped.mode == "custom":
                    gr.Warning(
                        duration=20,
                        title="",
                        message="""<div class="visible fr-p-2w">Le comparateur n'a pas pu piocher parmi les modèles sélectionnés car ils ne sont temporairement pas disponibles. Si vous réessayez, le comparateur piochera parmi d'autres modèles.</div>""",
                    )

                model_left, model_right = m.pick_two(
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
                conv_a_scoped.messages.append(
                    ChatMessage(role="user", content=original_user_prompt, error=str(e))
                )
                conv_b_scoped.messages.append(
                    ChatMessage(role="user", content=original_user_prompt, error=str(e))
                )
        finally:

            # Got answer at this point (or error?)
            app_state_scoped.awaiting_responses = False

            logger.debug(
                f"{app_state_scoped}, [{conv_a_scoped}, {conv_b_scoped}], {request}, {cohorts_comma_separated}"
            )

            record_conversations(
                app_state_scoped,
                [conv_a_scoped, conv_b_scoped],
                request,
                cohorts_comma_separated=cohorts_comma_separated,
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
                # banner
                gr.skip(),
                # textbox
                gr.skip(),
                # model_dropdown
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

        ip = get_ip(request)

        if redis_host and is_ratelimited(ip):
            logger.error(
                f"Too much text submitted for ip {ip}",
                extra={"request": request},
            )
            raise gr.Error(
                f"Trop de texte a été envoyé, veuillez réessayer dans quelques heures."
            )

        for i in range(2):
            conversations[i].messages.append(ChatMessage(role="user", content=text))
        conv_a_scoped = conversations[0]
        conv_b_scoped = conversations[1]
        app_state_scoped.awaiting_responses = True

        cohorts_comma_separated = retrieve_cohorts_redis(request.session_hash)
        record_conversations(
            app_state_scoped,
            [conv_a_scoped, conv_b_scoped],
            request,
            cohorts_comma_separated=cohorts_comma_separated,
        )

        chatbot = to_threeway_chatbot(conversations)
        text = gr.update(visible=True, value="")
        ip = get_ip(request)
        if conv_a_scoped.model_name in pricey_models:
            increment_input_chars(ip, len(text))
        if conv_b_scoped.model_name in pricey_models:
            increment_input_chars(ip, len(text))

        # FIXME running bot_response_multi directly here to receive messages on front
        yield from bot_response_multi(
            app_state_scoped,
            conv_a_scoped,
            conv_b_scoped,
            chatbot,
            text,
            request,
        )

    @gr.on(
        inputs=[app_state] + [conv_a] + [conv_b],
        outputs=[app_state] + [conv_a] + [conv_b] + [chatbot] + [textbox],
        api_name="chatbot_retry",
        show_progress="hidden",
    )
    def retry(
        app_state_scoped,
        conv_a_scoped: gr.State,
        conv_b_scoped: gr.State,
        request: gr.Request,
        event: gr.EventData,
    ):

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
        for i in range(2):
            conversations[i].messages.append(ChatMessage(role="user", content=text))
        conv_a_scoped = conversations[0]
        conv_b_scoped = conversations[1]
        app_state_scoped.awaiting_responses = True

        cohorts_comma_separated = retrieve_cohorts_redis(request.session_hash)
        record_conversations(
            app_state_scoped,
            [conv_a_scoped, conv_b_scoped],
            request,
            cohorts_comma_separated=cohorts_comma_separated,
        )

        chatbot = to_threeway_chatbot(conversations)

        # FIXME running bot_response_multi directly here to receive messages on front
        yield from bot_response_multi(
            app_state_scoped,
            conv_a_scoped,
            conv_b_scoped,
            chatbot,
            text,
            request,
        )

    def bot_response_multi(
        app_state_scoped,
        conv_a_scoped,
        conv_b_scoped,
        chatbot,
        textbox,
        request: gr.Request,
    ):
        try:
            gen_a = bot_response("a", conv_a_scoped, request)
            gen_b = bot_response("b", conv_b_scoped, request)
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
                # TODO: only capture model name to sort more easily in sentry
                sentry_sdk.capture_exception(e)

            error_reason = (
                f"error_during_convo: {error_with_model}, {error_with_endpoint}, {e}"
            )
            try:
                requests.post(
                    f"{settings.LANGUIA_CONTROLLER_URL}/models/{error_with_model}/error",
                    json={"error": error_reason},
                    timeout=1,
                )
            except:
                pass

            logger.exception(
                error_reason,
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

            cohorts_comma_separated = retrieve_cohorts_redis(request.session_hash)
            record_conversations(
                app_state_scoped,
                [conv_a_scoped, conv_b_scoped],
                request,
                cohorts_comma_separated=cohorts_comma_separated,
            )

            if conv_a_scoped.messages[-1].role != "user":
                logger.info(
                    f"response_modele_a ({conv_a_scoped.model_name}): {str(conv_a_scoped.messages[-1].content)}",
                    extra={"request": request},
                )
                logger.info(
                    f"response_modele_b ({conv_b_scoped.model_name}): {str(conv_b_scoped.messages[-1].content)}",
                    extra={"request": request},
                )

            chatbot = to_threeway_chatbot([conv_a_scoped, conv_b_scoped])

            yield [app_state_scoped, conv_a_scoped, conv_b_scoped, chatbot, textbox]

    def enable_conclude(
        app_state_scoped, textbox_scoped, conv_a_scoped, request: gr.Request
    ):
        # If last msg is from user, don't show send_btn and textbox
        if conv_a_scoped.messages[-1].role != "user":
            show_send_btn_and_textbox = True
        else:
            show_send_btn_and_textbox = False

        # don't enable conclude if only one user msg
        if len(conv_a_scoped.messages) in [0, 1]:
            enable_conclude_btn = False
        else:
            enable_conclude_btn = True
        return {
            textbox: gr.update(visible=show_send_btn_and_textbox),
            conclude_btn: gr.update(interactive=enable_conclude_btn),
            send_btn: gr.update(visible=show_send_btn_and_textbox),
        }

    gr.on(
        triggers=[
            model_dropdown.submit,
        ],
        fn=add_first_text,
        api_name="add_first_text",
        inputs=[app_state, model_dropdown, locale],
        outputs=[app_state]
        + [conv_a]
        + [conv_b]
        + [chatbot]
        + [textbox]
        + [header]
        + [textbox]
        + [model_dropdown]
        + [chat_area]
        + [send_btn]
        + [conclude_btn]
        + [send_area],
        show_progress="hidden",
        # TODO: refacto possible with .success() and more explicit error state
    )

    gr.on(
        triggers=[
            textbox.submit,
            send_btn.click,
            chatbot.retry,
        ],
        fn=add_text,
        api_name="add_text",
        inputs=[app_state] + [conv_a] + [conv_b] + [textbox],
        outputs=[app_state] + [conv_a] + [conv_b] + [chatbot] + [textbox],
        # scroll_to_output=True,
        show_progress="hidden",
    ).then(
        # gr.on(triggers=[chatbots[0].change,chatbots[1].change],
        fn=bot_response_multi,
        # inputs=conversations + [temperature, top_p, max_output_tokens],
        inputs=[app_state] + [conv_a] + [conv_b] + [chatbot] + [textbox],
        outputs=[app_state, conv_a, conv_b, chatbot, textbox],
        api_name=False,
        show_progress="hidden",
        # scroll_to_output=True,
        # TODO: refacto possible with .success() and more explicit error state
    )

    def force_vote_or_reveal(
        app_state_scoped, conv_a_scoped, conv_b_scoped, request: gr.Request
    ):

        for reaction in app_state_scoped.reactions:
            if reaction and reaction["liked"] != None:
                logger.info("meaningful_reaction")
                logger.debug(reaction)
                break
        # If no break found
        else:
            logger.debug("no meaningful reaction found, inflicting vote screen")
            logger.info(
                "ecran_vote",
                extra={"request": request},
            )
            return {
                chatbot: gr.update(interactive=False),
                send_area: gr.update(visible=False),
                vote_area: gr.update(
                    elem_classes="fr-container min-h-screen fr-pt-4w next-screen",
                    visible=True,
                ),
                buttons_footer: gr.update(visible=True),
            }

        if len(conv_a_scoped.messages) == 2:
            your_choice_badge = determine_choice_badge(app_state_scoped.reactions)
        else:
            your_choice_badge = None

        chosen_model = get_chosen_model(your_choice_badge)
        reveal_dict = build_reveal_dict(conv_a_scoped, conv_b_scoped, chosen_model)

        return reveal_dict

    gr.on(
        triggers=[conclude_btn.click],
        inputs=[app_state, conv_a, conv_b],
        outputs=reveal_data,
        api_name="reveal",
        fn=force_vote_or_reveal,
        # scroll_to_output=True,
        show_progress="hidden",
    )

    @gr.on(
        inputs=[app_state] + [conv_a] + [conv_b] + [chatbot] + [reaction_json],
        outputs=[app_state],
        api_name="chatbot_react",
    )
    def record_like_json(
        app_state_scoped,
        conv_a_scoped,
        conv_b_scoped,
        chatbot,
        reaction_json,
        request: gr.Request,
    ):
        # FIXME comment disappear if select a pref after commenting

        # A comment is always on an existing reaction, but the like event on commenting doesn't give you the full reaction, it could though
        # TODO: or just create another event type like "Event.react"
        if reaction_json:
            if "comment" in reaction_json:
                app_state_scoped.reactions[reaction_json["index"]]["comment"] = (
                    reaction_json["comment"]
                )
            else:
                while len(app_state_scoped.reactions) <= reaction_json["index"]:
                    app_state_scoped.reactions.extend([None])
                app_state_scoped.reactions[reaction_json["index"]] = reaction_json

        sync_reactions(
            conv_a_scoped,
            conv_b_scoped,
            chatbot,
            # chatbot.messages,
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

        chosen_model = get_chosen_model(which_model_radio_output)
        reveal_dict = build_reveal_dict(conv_a_scoped, conv_b_scoped, chosen_model)

        return reveal_dict

    gr.on(
        triggers=[supervote_send_btn.click],
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
        outputs=reveal_data,
        # outputs=[quiz_modal],
        api_name="chatbot_vote",
        # scroll_to_output=True,
        show_progress="hidden",
    )
