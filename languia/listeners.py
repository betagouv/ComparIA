from languia.block_arena import (
    app_state,
    buttons_footer,
    chat_area,
    chatbot,
    comments_a,
    comments_b,
    comments_link,
    conclude_btn,
    conv_a,
    conv_b,
    demo,
    guided_cards,
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
    textbox,
    vote_area,
    which_model_radio,
)
import traceback
import os
import sentry_sdk
import uuid
from time import sleep
import openai

from languia.utils import (
    get_ip,
    get_matomo_tracker_from_cookies,
    get_battle_pair,
    refresh_outages,
    on_endpoint_error,
    gen_prompt,
    to_threeway_chatbot,
    EmptyResponseError,
    pick_endpoint,
)

from languia.reveal import build_reveal_html, determine_choice_badge

from languia.logs import vote_last_response, sync_reactions, record_conversations

from languia.config import (
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    SAMPLING_WEIGHTS,
    BATTLE_TARGETS,
    SAMPLING_BOOST_MODELS,
)

# from fastchat.model.model_adapter import get_conversation_template

from languia.conversation import (
    bot_response,
    set_conv_state
)


import gradio as gr


from languia.config import logger


from languia import config

from custom_components.customchatbot.backend.gradio_customchatbot.customchatbot import (
    ChatMessage,
)


# Register listeners
def register_listeners():

    # Step 0

    def enter_arena(
        app_state_scoped, conv_a_scoped, conv_b_scoped, request: gr.Request
    ):

        # /!\ careful about user state / shared state if moving this function
        def init_conversations(
            app_state_scoped, conv_a_scoped, conv_b_scoped, request: gr.Request
        ):
            app_state_scoped.awaiting_responses = False
            config.outages = refresh_outages(
                config.outages, controller_url=config.controller_url
            )

            # outages = [outage.get("api_id") for outage in config.outages]
            outages = config.outages
            # app_state.model_left, app_state.model_right = get_battle_pair(
            model_left, model_right = get_battle_pair(
                config.models,
                BATTLE_TARGETS,
                outages,
                SAMPLING_WEIGHTS,
                SAMPLING_BOOST_MODELS,
            )
            endpoint_left = pick_endpoint(model_left, outages)
            endpoint_right = pick_endpoint(model_right, outages)
            # TODO: replace by class method
            conv_a_scoped = set_conv_state(
                conv_a_scoped, model_name=model_left, endpoint=endpoint_left
            )
            conv_b_scoped = set_conv_state(
                conv_b_scoped, model_name=model_right, endpoint=endpoint_right
            )
            logger.info(
                f"selection_modeles: {model_left}, {model_right}",
                extra={request: request},
            )

            logger.info(
                f"conv_pair_id: {conv_a_scoped.conv_id}-{conv_b_scoped.conv_id}",
                extra={request: request},
            )
            return conv_a_scoped, conv_b_scoped

        # TODO: actually check for it
        # tos_accepted = request...
        # if tos_accepted:
        logger.info(
            f"init_arene, session_hash: {request.session_hash}, IP: {get_ip(request)}, cookie: {(get_matomo_tracker_from_cookies(request.cookies))}",
            extra={"request": request},
        )
        app_state_scoped.awaiting_responses = False
        conv_a_scoped, conv_b_scoped = init_conversations(
            app_state_scoped, conv_a_scoped, conv_b_scoped, request
        )
        return [app_state_scoped, conv_a_scoped, conv_b_scoped]

    gr.on(
        triggers=[demo.load],
        fn=enter_arena,
        inputs=[app_state, conv_a, conv_b],
        outputs=[app_state, conv_a, conv_b],
        api_name=False,
        show_progress="hidden",
        # concurrency_limit=None
    ).then(
        fn=(lambda: None),
        inputs=None,
        outputs=None,
        js="""(args) => {
setTimeout(() => {

const cookieExists = document.cookie.includes('comparia_already_visited');
if (!cookieExists) {
    document.cookie = 'name=comparia_already_visited; SameSite=None; Secure;'
    const modal = document.getElementById("fr-modal-welcome");
    dsfr(modal).modal.disclose();
}
document.getElementById("fr-modal-welcome-close").blur();
}, 500);

}""",
    )

    # Step 1

    # Step 1.1
    @guided_cards.change(
        inputs=[app_state, guided_cards],
        outputs=[app_state, send_btn, send_area, textbox, shuffle_link],
        api_name=False,
        show_progress="hidden",
    )
    def set_guided_prompt(
        app_state_scoped, guided_cards, event: gr.EventData, request: gr.Request
    ):

        # chosen_prompts_pool = guided_cards
        category = guided_cards
        prompt = gen_prompt(category)
        app_state_scoped.category = category

        logger.info(
            f"categorie_{category}: {prompt}",
            extra={"request": request},
        )
        return {
            app_state: app_state_scoped,
            send_btn: gr.update(interactive=True),
            send_area: gr.update(visible=True),
            textbox: gr.update(value=prompt),
            shuffle_link: gr.update(visible=True),
        }

    @shuffle_link.click(
        inputs=[guided_cards], outputs=[textbox], api_name=False, show_progress="hidden"
    )
    def shuffle_prompt(guided_cards, request: gr.Request):
        prompt = gen_prompt(guided_cards)
        logger.info(
            f"shuffle: {prompt}",
            extra={"request": request},
        )
        return prompt

    @textbox.change(
        inputs=[app_state, textbox],
        outputs=send_btn,
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

    def add_text(
        app_state_scoped,
        conv_a_scoped: gr.State,
        conv_b_scoped: gr.State,
        text: gr.Text,
        request: gr.Request,
        event: gr.EventData,
    ):
        # if retry, resend last user errored message
        if event._data is not None:
            logger.info("Received event+retry with:")
            last_message_a = conv_a_scoped.messages[-1]
            last_message_b = conv_b_scoped.messages[-1]
            logger.info("conv_a:"+ str(conv_a_scoped.messages))
            logger.info("conv_b:"+ str(conv_b_scoped.messages))
            app_state_scoped.awaiting_responses = False
            if last_message_a.role == "user" and last_message_b.role == "user":
                text = last_message_a.content
                conv_a_scoped.messages = conv_a_scoped.messages[:-1]
                conv_b_scoped.messages = conv_b_scoped.messages[:-1]
            else:
                raise gr.Error(
                    message="Il n'est pas possible de réessayer, veuillez recharger la page.",
                    duration=10,
                )
            # # Reinit both generators
            # gen = [
            #     bot_response(
            #         pos[i],
            #         conversations[i],
            #         request,
            #         apply_rate_limit=True,
            #         use_recommended_config=True,
            #     )
            #     for i in range(config.num_sides)
            # ]

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
            # conversations[i].messages.append(ChatMessage(role="user", content="Placeholder to test errors on turn 2"))
            # conversations[i].messages.append(ChatMessage(role="assistant", content="Placeholder to test errors on turn 2"))
            conversations[i].messages.append(ChatMessage(role="user", content=text))
        conv_a_scoped = conversations[0]
        conv_b_scoped = conversations[1]
        app_state_scoped.awaiting_responses = True

        # record for questions only dataset and stats on ppl abandoning before generation completion
        record_conversations(app_state_scoped, [conv_a_scoped, conv_b_scoped], request)

        chatbot = to_threeway_chatbot(conversations)
        text = gr.update(visible=True)
        return [
            app_state_scoped,
            # 2 conversations
            conv_a_scoped,
            conv_b_scoped,
            # 1 chatbot
            chatbot,
            text,
        ]

    def goto_chatbot(
        request: gr.Request,
        #  FIXME: ignored
        api_name=False,
    ):
        logger.debug("goto_chatbot")
        return {
            textbox: gr.update(
                value="",
                placeholder="Continuer à discuter avec les deux modèles d'IA",
            ),
            mode_screen: gr.update(visible=False),
            chat_area: gr.update(visible=True),
            send_btn: gr.update(interactive=False),
            shuffle_link: gr.update(visible=False),
            conclude_btn: gr.update(visible=True, interactive=False),
        }

    def bot_response_multi(
        app_state_scoped,
        conv_a_scoped,
        conv_b_scoped,
        chatbot,
        textbox,
        request: gr.Request,
    ):
        conversations = [conv_a_scoped, conv_b_scoped]
        pos = ["a", "b"]

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
            # When context is too long, Albert API answers:
            # openai.BadRequestError: Error code: 400 - {'detail': 'Context length too large'}
            # When context is too long, HF API answers:
            # "openai.APIError: An error occurred during streaming"
            # TODO: timeout problems on scaleway Ampere models?
            # except httpcore.ReadTimeout:
            #     pass
            # except httpx.ReadTimeout:
            #     pass
        except (
            BaseException,
            openai.APIError,
            openai.BadRequestError,
            EmptyResponseError,
        ) as e:
            error_with_endpoint = conversations[i].endpoint.get("api_id")
            error_with_model = conversations[i].model_name

            if os.getenv("SENTRY_DSN"):

                with sentry_sdk.configure_scope() as scope:
                    # Set the fingerprint based on the message content
                    scope.fingerprint = [e]
                    sentry_sdk.capture_exception(e, scope)

            logger.exception(
                f"erreur_modele: {error_with_model}, {error_with_endpoint}, '{e}'\n{traceback.format_exc()}",
                extra={
                    "request": request,
                    "error": str(e),
                    "stacktrace": traceback.format_exc(),
                },
                exc_info=True,
            )

            # Remove last message if it's an assistant message (failed during generation)
            if conv_a_scoped.messages[-1].role == "assistant":
                conv_a_scoped.messages = conv_a_scoped.messages[:-1]
            if conv_b_scoped.messages[-1].role == "assistant":
                conv_b_scoped.messages = conv_b_scoped.messages[:-1]
                
            conv_a_scoped.messages[-1].error = True
            conv_b_scoped.messages[-1].error = True


    
            # Report error to controller
            # on_endpoint_error(
            #     config.controller_url,
            #     error_with_endpoint,
            #     reason=str(e),
            # )

            # If it's the first message in conversation, re-roll
            # TODO: need to be adapted to template logic (first messages could already have a >2 length if not zero-shot)
            if len(conv_a_scoped.messages) == 1:
                original_user_prompt = conv_a_scoped.messages[0].content
                
                config.outages = refresh_outages(
                    config.outages, controller_url=config.controller_url
                )

                logger.debug(
                    "refreshed outage models:" + str(config.outages)
                )  # Simpler to repick 2 models
                model_left, model_right = get_battle_pair(
                    config.models,
                    BATTLE_TARGETS,
                    config.outages,
                    SAMPLING_WEIGHTS,
                    SAMPLING_BOOST_MODELS,
                )


                conv_a_scoped = set_conv_state(
                    conv_a_scoped,
                    model_name=model_left,
                    endpoint=pick_endpoint(model_left, config.outages),
                )
                conv_b_scoped = set_conv_state(
                    conv_b_scoped,
                    model_name=model_right,
                    endpoint=pick_endpoint(model_right, config.outages),
                )
                conv_a_scoped.messages.append(
                    ChatMessage(role="user", content=original_user_prompt, error=True)
                )
                conv_b_scoped.messages.append(
                    ChatMessage(role="user", content=original_user_prompt, error=True)
                )

        # Got answer at this point
        app_state_scoped.awaiting_responses = False

        record_conversations(app_state_scoped, [conv_a_scoped, conv_b_scoped], request)

        if not conv_a_scoped.messages[-1].role == "user":
            logger.info(
                f"response_modele_a ({conv_a_scoped.model_name}): {str(conv_a_scoped.messages[-1].content)}",
                extra={"request": request},
            )
            logger.info(
                f"response_modele_b ({conv_b_scoped.model_name}): {str(conv_b_scoped.messages[-1].content)}",
                extra={"request": request},
            )
        print("conv_a_scoped.messages")
        print(conv_a_scoped.messages)
        print("conv_b_scoped.messages")
        print(conv_b_scoped.messages)
        
        chatbot = to_threeway_chatbot([conv_a_scoped, conv_b_scoped])
        # conv_a_scoped = conversations[0]
        # conv_b_scoped = conversations[1]
        # print("conversations:")
        # print(conversations[0].messages)
        # print(conversations[1].messages)
        # hide textbox when retrying ?
        return [app_state_scoped, conv_a_scoped, conv_b_scoped, chatbot, textbox]

    # don't enable conclude if only one user msg
    def enable_conclude(
        app_state_scoped, textbox_scoped, conv_a_scoped, request: gr.Request
    ):
        if len(conv_a_scoped.messages) == 0:
            return { textbox: gr.update(visible=True),
                    conclude_btn: gr.skip(),
                    send_btn: gr.skip()
            }
        if len(conv_a_scoped.messages) == 1:
            return {
                    textbox: gr.update(visible=False),
                    conclude_btn: gr.skip(),
                    send_btn: gr.update(visible=False),
                }
        if conv_a_scoped.messages[-1].role == "user":
            return {
                textbox: gr.update(visible=False),
                conclude_btn: gr.update(interactive=True),
                send_btn: gr.update(visible=False),
            }
        return {
                textbox: gr.update(visible=True),
                conclude_btn: gr.update(interactive=True),
                send_btn: gr.update(visible=True),
            }


    gr.on(
        triggers=[textbox.submit, send_btn.click, chatbot.retry],
        fn=add_text,
        api_name=False,
        inputs=[app_state] + [conv_a] + [conv_b] + [textbox],
        outputs=[app_state] + [conv_a] + [conv_b] + [chatbot] + [textbox],
        # scroll_to_output=True,
        show_progress="hidden",
    ).success(
        fn=goto_chatbot,
        inputs=[],
        outputs=(
            [textbox]
            + [mode_screen]
            + [chat_area]
            + [send_btn]
            + [shuffle_link]
            + [conclude_btn]
        ),
        show_progress="hidden",
        # scroll_to_output=True
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
    )
    # // Enable navigation prompt
    # window.onbeforeunload = function() {
    #     return true;
    # };
    # // Remove navigation prompt
    # window.onbeforeunload = null;

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

        reveal_html = build_reveal_html(
            conv_a_scoped,
            conv_b_scoped,
            which_model_radio=your_choice_badge,
        )
        return {
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
const nextScreen = document.querySelector('.next-screen');
nextScreen.scrollIntoView({
  behavior: 'smooth',
  block: 'start'
});}, 500);
}""",
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

        reveal_html = build_reveal_html(
            conv_a=conv_a_scoped,
            conv_b=conv_b_scoped,
            which_model_radio=which_model_radio_output,
        )
        return {
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
            app_state,
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
    )

    # gr.on(
    #     triggers=retry_modal_btn.click,
    #     fn=(lambda: Modal(visible=True)),
    #     inputs=[],
    #     outputs=retry_modal,
    #     api_name=False,
    # )
    # gr.on(
    #     triggers=close_retry_modal_btn.click,
    #     fn=(lambda: Modal(visible=False)),
    #     inputs=[],
    #     outputs=retry_modal,
    #     api_name=False,
    # )

    # On reset go to mode selection mode_screen

    # gr.on(
    #     triggers=[retry_btn.click],
    #     api_name=False,
    #     # triggers=[clear_btn.click, retry_btn.click],
    #     fn=clear_history,
    #     inputs=conversations + [chatbot] + [textbox],
    # )

    # def clear_history(
    #     request: gr.Request,
    # ):
    # return
