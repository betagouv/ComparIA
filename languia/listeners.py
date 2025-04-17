from languia.block_arena import (
    app_state,
    buttons_footer,
    chat_area,
    CustomDropdown,
    CustomChatbot,
    chatbot,
    comments_a,
    comments_b,
    comments_link,
    conclude_btn,
    conv_a,
    conv_b,
    demo,
    guided_cards,
    header,
    mode_screen,
    negative_a,
    negative_b,
    positive_a,
    positive_b,
    results_area,
    reveal_screen,
    send_area,
    send_btn,
    shuffle_link,
    supervote_area,
    supervote_send_btn,
    # first_textbox,
    textbox,
    vote_area,
    which_model_radio,
    model_dropdown,
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
    refresh_unavailable_models,
    gen_prompt,
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

from custom_components.customchatbot.backend.gradio_customchatbot.customchatbot import (
    ChatMessage,
)


# Register listeners
def register_listeners():

    # Step 0

    def enter_arena(request: gr.Request):
        # Refresh on picking model? Do it async? Should do it globally and async...
        config.unavailable_models = refresh_unavailable_models(
            config.unavailable_models, controller_url=config.controller_url
        )

        # TODO: actually check for it
        # tos_accepted = request...
        # if tos_accepted:
        logger.info(
            f"init_arene, session_hash: {request.session_hash}, IP: {get_ip(request)}, cookie: {(get_matomo_tracker_from_cookies(request.cookies))}",
            extra={"request": request},
        )

    gr.on(
        triggers=[demo.load],
        fn=enter_arena,
        inputs=None,
        outputs=None,
        api_name=False,
        show_progress="hidden",
        # concurrency_limit=None
        js="""(args) => {
setTimeout(() => {

const cookieExists = document.cookie.includes('comparia_already_visited');
document.cookie = 'comparia_already_visited=true; SameSite=Strict; Secure; Path=/;'
if (!cookieExists) {
    const modal = document.getElementById("fr-modal-welcome");
    dsfr(modal).modal.disclose();
}
document.getElementById("fr-modal-welcome-close").blur();
}, 500);

}""",
    )

    # Step 1

    # Step 1.1
    @guided_cards.input(
        inputs=[app_state, guided_cards, model_dropdown],
        outputs=[app_state, model_dropdown, shuffle_link],
        api_name=False,
        show_progress="hidden",
    )
    def set_guided_prompt(
        app_state_scoped,
        guided_cards,
        model_dropdown_scoped,
        event: gr.EventData,
        request: gr.Request,
    ):

        # chosen_prompts_pool = guided_cards
        category = guided_cards
        prompt = gen_prompt(category)
        app_state_scoped.category = category

        logger.info(
            f"categorie_{category}: {prompt}",
            extra={"request": request},
        )
        new_value = prompt

        model_dropdown_scoped["prompt_value"] = new_value

        return {
            app_state: app_state_scoped,
            # first_send_btn: gr.update(interactive=True),
            model_dropdown: model_dropdown_scoped,
            shuffle_link: gr.update(visible=True),
        }

    @shuffle_link.click(
        inputs=[guided_cards, model_dropdown],
        outputs=[model_dropdown],
        api_name=False,
        show_progress="hidden",
    )
    def shuffle_prompt(guided_cards, model_dropdown_scoped, request: gr.Request):
        prompt = gen_prompt(guided_cards)
        model_dropdown_scoped["prompt_value"] = prompt
        logger.info(
            f"shuffle: {prompt}",
            extra={"request": request},
        )
        return model_dropdown_scoped

    @textbox.change(
        inputs=[app_state, textbox],
        outputs=[send_btn],
        api_name=False,
        show_progress="hidden",
    )
    def change_send_btn_state(app_state_scoped, textbox):
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
        request: gr.Request,
        # event: gr.EventData,
    ):
        # Already refreshed in enter_arena, but not refreshed if add_first_text accessed directly
        # TODO: replace outage detection with disabling models + use litellm w/ routing and outage detection
        config.unavailable_models = refresh_unavailable_models(
            config.unavailable_models, controller_url=config.controller_url
        )
        didnt_reset_prompt = True
        text = model_dropdown_scoped.get("prompt_value", "")
        mode = model_dropdown_scoped.get("mode", "random")
        app_state_scoped.mode = mode
        custom_models_selection = model_dropdown_scoped.get(
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
            mode, custom_models_selection, unavailable_models=config.unavailable_models
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
                    # 1 chatbot
                    chatbot,
                    text,
                    banner,
                    # textbox
                    new_textbox,
                    # mode_screen
                    gr.update(visible=False),
                    # chat_area
                    gr.update(visible=True),
                    # send_btn
                    gr.update(interactive=False),
                    # shuffle_link
                    gr.update(visible=False),
                    # conclude_btn
                    gr.update(visible=True, interactive=False),
                    gr.update(visible=True),
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

                config.unavailable_models = refresh_unavailable_models(
                    config.unavailable_models, controller_url=config.controller_url
                )

                logger.debug(
                    "refreshed outage models:" + str(config.unavailable_models)
                )  # Simpler to repick 2 models

                if app_state_scoped.mode == "custom":
                    gr.Warning(
                        duration=20,
                        title="",
                        message="""<div class="visible fr-p-2w">Le comparateur n'a pas pu piocher parmi les modèles sélectionnés car ils ne sont temporairement pas disponibles. Si vous réessayez, le comparateur piochera parmi d'autres modèles.</div>""",
                    )

                model_left, model_right = pick_models(
                    app_state_scoped.mode,
                    # Doesn't make sense to keep custom model options here
                    # FIXME: if error with model wasn't the one chosen (case where you select only one model) just reroll the other one
                    [],
                    # temporarily exclude the buggy model here
                    config.unavailable_models + [error_with_model],
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
                # shuffle_link
                gr.update(visible=False),
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
        return [
            app_state_scoped,
            # 2 conversations
            conv_a_scoped,
            conv_b_scoped,
            # 1 chatbot
            chatbot,
            text,
        ]

    def bot_response_multi(
        app_state_scoped,
        conv_a_scoped,
        conv_b_scoped,
        chatbot,
        textbox,
        request: gr.Request,
    ):
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
        api_name=False,
        inputs=[app_state, model_dropdown],
        outputs=[app_state]
        + [conv_a]
        + [conv_b]
        + [chatbot]
        + [textbox]
        + [header]
        + [textbox]
        + [mode_screen]
        + [chat_area]
        + [send_btn]
        + [shuffle_link]
        + [conclude_btn]
        + [send_area],
        show_progress="hidden",
        # TODO: refacto possible with .success() and more explicit error state
    ).then(
        fn=enable_conclude,
        inputs=[app_state, textbox, conv_a],
        outputs=[textbox, conclude_btn, send_btn],
        js="""(args) => {
setTimeout(() => {
  console.log("scrolling to bot responses");
  var botRows = document.querySelectorAll('.bot-row');
    var lastBotRow = botRows.item(botRows.length - 1);
    lastBotRow.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });
  }
, 500);
}""",
        show_progress="hidden",
    )

    gr.on(
        triggers=[
            textbox.submit,
            send_btn.click,
            chatbot.retry,
        ],
        fn=add_text,
        api_name=False,
        inputs=[app_state] + [conv_a] + [conv_b] + [textbox],
        outputs=[app_state] + [conv_a] + [conv_b] + [chatbot] + [textbox],
        # scroll_to_output=True,
        show_progress="hidden",
    ).then(
        fn=(lambda: None),
        inputs=None,
        outputs=None,
        js="""(args) => {
setTimeout(() => {
  console.log("scrolling to last user row if there are at least 2 user rows");
  var userRows = document.querySelectorAll('.user-row');
  if (userRows.length >= 2) {
    var lastUserRow = userRows.item(userRows.length - 1);
    lastUserRow.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });
  }
}, 500);
}""",
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
    ).then(
        fn=enable_conclude,
        inputs=[app_state, textbox, conv_a],
        outputs=[textbox, conclude_btn, send_btn],
        js="""(args) => {
setTimeout(() => {
  console.log("scrolling to bot responses");
  var botRows = document.querySelectorAll('.bot-row');
    var lastBotRow = botRows.item(botRows.length - 1);
    lastBotRow.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });
  }
, 500);
}""",
        show_progress="hidden",
    )

    def force_vote_or_reveal(
        app_state_scoped, conv_a_scoped, conv_b_scoped, request: gr.Request
    ):

        for reaction in app_state_scoped.reactions:
            if reaction:
                if reaction["liked"] != None:
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

        banner = second_header_html(2)

        reveal_html = build_reveal_html(
            conv_a_scoped,
            conv_b_scoped,
            which_model_radio=your_choice_badge,
        )
        return {
            header: gr.update(value=banner),
            chatbot: gr.update(interactive=False),
            send_area: gr.update(visible=False),
            reveal_screen: gr.update(
                elem_classes="min-h-screen fr-pt-4w  next-screen", visible=True
            ),
            results_area: gr.update(value=reveal_html),
            # buttons_footer: gr.update(visible=False),
        }

    gr.on(
        triggers=[conclude_btn.click],
        inputs=[app_state, conv_a, conv_b],
        outputs=[
            chatbot,
            header,
            send_area,
            vote_area,
            buttons_footer,
            reveal_screen,
            results_area,
            buttons_footer,
        ],
        api_name=False,
        fn=force_vote_or_reveal,
        # scroll_to_output=True,
        show_progress="hidden",
    ).then(
        fn=(lambda: None),
        inputs=None,
        outputs=None,
        js="""(args) => {
        console.log("args:")
        console.log(args)
setTimeout(() => {
console.log("scrolling to .next-screen");
const chatArea = document.getElementById('chat-area');
chatArea.style.paddingBottom = `0px`;

let secondHeader = document.getElementById('second-header');
const secondHeaderHeight = secondHeader.offsetHeight;

// const nextScreen = document.querySelector('.next-screen');
window.scrollTo({
  top: secondHeaderHeight + chatArea.offsetHeight,
  left: 0,
  behavior: 'smooth',
  });}, 500);
}""",
        show_progress="hidden",
    )

    @chatbot.like(
        inputs=[app_state] + [conv_a] + [conv_b] + [chatbot],
        outputs=[app_state],
        api_name=False,
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

    @which_model_radio.select(
        inputs=[which_model_radio],
        outputs=[supervote_area, supervote_send_btn],
        api_name=False,
        show_progress="hidden",
    )
    def build_supervote_area(vote_radio, request: gr.Request):
        logger.info(
            "vote_selection_temp:" + str(vote_radio),
            extra={"request": request},
        )

        # outputs=[supervote_area, supervote_send_btn, why_vote] +
        # relevance_slider: gr.update(interactive=False),
        # form_slider: gr.update(interactive=False),
        # style_slider: gr.update(interactive=False),
        # comments_text: gr.update(interactive=False),
        return [
            gr.update(visible=True),
            gr.update(interactive=True),
        ]

    # Step 3
    @comments_link.click(
        outputs=[comments_a, comments_b, comments_link],
        api_name=False,
        show_progress="hidden",
    )
    def show_comments():
        return [gr.update(visible=True)] * 2 + [gr.update(visible=False)]

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
        banner = second_header_html(2)

        reveal_html = build_reveal_html(
            conv_a=conv_a_scoped,
            conv_b=conv_b_scoped,
            which_model_radio=which_model_radio_output,
        )
        return {
            header: gr.update(value=banner),
            positive_a: gr.update(interactive=False),
            positive_b: gr.update(interactive=False),
            negative_a: gr.update(interactive=False),
            negative_b: gr.update(interactive=False),
            comments_a: gr.update(interactive=False),
            comments_b: gr.update(interactive=False),
            comments_link: gr.update(interactive=False),
            which_model_radio: gr.update(interactive=False),
            reveal_screen: gr.update(visible=True),
            results_area: gr.update(value=reveal_html),
            buttons_footer: gr.update(visible=False),
        }

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
        outputs=[
            header,
            positive_a,
            positive_b,
            negative_a,
            negative_b,
            comments_a,
            comments_b,
            comments_link,
            reveal_screen,
            results_area,
            buttons_footer,
            which_model_radio,
        ],
        # outputs=[quiz_modal],
        api_name=False,
        # scroll_to_output=True,
        show_progress="hidden",
    ).then(
        fn=(lambda: None),
        inputs=None,
        outputs=None,
        js="""(args) => {
setTimeout(() => {
console.log("scrolling to #reveal-screen");

const voteArea = document.getElementById('vote-area');
voteArea.classList.remove("min-h-screen");

const revealScreen = document.getElementById('reveal-screen');
revealScreen.scrollIntoView({
  behavior: 'smooth',
  block: 'start'
});}, 500);
}""",
        show_progress="hidden",
    )
