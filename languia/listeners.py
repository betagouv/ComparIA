from languia.block_arena import *
import traceback

import uuid

import openai

from languia.utils import (
    get_ip,
    get_matomo_tracker_from_cookies,
    get_battle_pair,
    build_reveal_html,
    vote_last_response,
    get_model_extra_info,
    count_output_tokens,
    get_llm_impact,
    refresh_outage_models,
    add_outage_model,
    gen_prompt,
    to_threeway_chatbot,
    EmptyResponseError,
)

from languia.config import (
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    SAMPLING_WEIGHTS,
    BATTLE_TARGETS,
    SAMPLING_BOOST_MODELS,
)

# from fastchat.model.model_adapter import get_conversation_template

from languia.block_conversation import (
    bot_response,
)


import gradio as gr


from languia.config import logger


from languia import config


# Register listeners
def register_listeners():

    # Step 0

    @demo.load(
        inputs=[conv_a, conv_b],
        outputs=[conv_a, conv_b],
        api_name=False,
        show_progress="hidden",
    )
    def enter_arena(conv_a, conv_b, request: gr.Request):

        # TODO: to get rid of!
        def set_conv_state(state, model_name=""):
            # self.messages = get_conversation_template(model_name)
            state.messages = []
            state.output_tokens = None

            # TODO: get it from api if generated
            state.conv_id = uuid.uuid4().hex

            # TODO: add template info? and test it
            state.template_name = "zero_shot"
            state.template = []
            state.model_name = model_name
            return state

        # you can't move this function out, that way app_state is dependent on each user state / not global state
        def init_conversations(conversations, request: gr.Request):
            app_state.awaiting_responses = False
            config.outage_models = refresh_outage_models(
                config.outage_models, controller_url=config.controller_url
            )
            # app_state.model_left, app_state.model_right = get_battle_pair(
            model_left, model_right = get_battle_pair(
                config.models,
                BATTLE_TARGETS,
                config.outage_models,
                SAMPLING_WEIGHTS,
                SAMPLING_BOOST_MODELS,
            )
            # TODO: to get rid of!
            conversations = [
                set_conv_state(conversations[0], model_name=model_left),
                set_conv_state(conversations[1], model_name=model_right),
            ]
            logger.info(
                f"selection_modeles: {model_left}, {model_right}",
                extra={request: request},
            )
            return {conv_a: conversations[0], conv_b: conversations[1]}

        # TODO: actually check for it
        # tos_accepted = request...
        # if tos_accepted:
        logger.info(
            f"init_arene, IP: {get_ip(request)}, cookie: {(get_matomo_tracker_from_cookies(request.cookies))}",
            extra={"request": request},
        )
        conv_a, conv_b = init_conversations([conv_a, conv_b], request)
        return [conv_a, conv_b]

    # Step 1

    # Step 1.1
    @guided_cards.change(
        inputs=[guided_cards],
        outputs=[send_btn, send_area, textbox, shuffle_link],
        api_name=False,
        show_progress="hidden",
    )
    def set_guided_prompt(guided_cards, event: gr.EventData, request: gr.Request):

        # chosen_prompts_pool = guided_cards
        category = guided_cards
        prompt = gen_prompt(category)
        app_state.category = category

        logger.info(
            f"categorie_{category}: {prompt}",
            extra={"request": request},
        )
        return {
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

    # @textbox.change(
    #     inputs=textbox, outputs=send_btn, api_name=False, show_progress="hidden"
    # )
    # def change_send_btn_state(textbox):
    #     if textbox == "" or (
    #         hasattr(app_state, "awaiting_responses") and app_state.awaiting_responses
    #     ):
    #         return gr.update(interactive=False)
    #     else:
    #         return gr.update(interactive=True)

    def add_text(
        app_state: gr.State,
        conv_a: gr.State,
        conv_b: gr.State,
        text: gr.Text,
        request: gr.Request,
    ):

        conversations = [conv_a, conv_b]

        # Check if "Enter" pressed and no text or still awaiting response and return early
        if text == "":
            raise (ValueError("Veuillez entrer votre texte."))
        if hasattr(app_state, "awaiting_responses") and app_state.awaiting_responses:
            raise (
                ValueError(
                    "Veuillez attendre la fin de la réponse des modèles avant de renvoyer une question."
                )
            )

        # FIXME: turn on moderation in battle mode
        # flagged = moderation_filter(all_conv_text, model_list, do_moderation=False)
        # if flagged:
        #     logger.info(f"violate moderation (anony). ip: {ip}. text: {text}")
        #     # overwrite the original text
        #     text = MODERATION_MSG

        # FIXME:  CONVERSATION_TURN_LIMIT:
        #     logger.info(f"conversation turn limit. ip: {get_ip(request)}. text: {text}")

        logger.info(
            f"msg_user: {text}",
            extra={"request": request},
        )
        text = text[:BLIND_MODE_INPUT_CHAR_LEN_LIMIT]  # Hard cut-off
        # TODO: what do?

        if len(conversations[0].messages) == 0:
            app_state.original_user_prompt = text
            logger.debug(
                "Saving original prompt: " + app_state.original_user_prompt,
                extra={"request": request},
            )

        for i in range(config.num_sides):
            conversations[i].messages.append(gr.ChatMessage(role="user", content=text))
        conv_a = conversations[0]
        conv_b = conversations[1]
        app_state.awaiting_responses = True
        chatbot = to_threeway_chatbot(conversations)
        return [
            app_state,
            # 2 conversations
            conv_a,
            conv_b,
            # 1 chatbot
            chatbot,
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
        app_state,
        conv_a,
        conv_b,
        chatbot,
        textbox,
        request: gr.Request,
    ):
        conversations = [conv_a, conv_b]

        gen = []
        for attempt in range(10):
            try:
                for i in range(config.num_sides):
                    gen.append(
                        bot_response(
                            conversations[i],
                            request,
                            apply_rate_limit=True,
                            use_recommended_config=True,
                        )
                    )

                iters = 0
                while True:
                    stop = True
                    iters += 1
                    for i in range(config.num_sides):
                        try:
                            # # Artificially slow faster Google Vertex API
                            # if not (model_api_dict["api_type"] == "vertex" and i % 15 != 0):
                            # if iters % 30 == 1 or iters < 3:
                            ret = next(gen[i])
                            conversations[i] = ret
                            stop = False
                        # When context is too long, Albert apis answer:
                        # openai.BadRequestError: Error code: 400 - {'detail': 'Context length too large'}
                        # When context is too long, HF apis answer:
                        # "openai.APIError: An error occurred during streaming"
                        except (openai.APIError, openai.BadRequestError):
                            # logger.error(
                            #     f"erreur_milieu_discussion: {conversations[i].model_name}"
                            # )
                            raise
                        except EmptyResponseError as e:

                            # logger.error(
                            #     f"erreur_milieu_discussion: {conversations[i].model_name}"
                            # )
                            raise e
                        except StopIteration:
                            pass
                        # TODO: timeout problems on scaleway Ampere models?
                        # except httpcore.ReadTimeout:
                        #     pass
                        # except httpx.ReadTimeout:
                        #     pass
                    conv_a = conversations[0]
                    conv_b = conversations[1]
                    chatbot = to_threeway_chatbot(conversations)
                    yield [app_state, conv_a, conv_b, chatbot, gr.skip()]
                    if stop:
                        break
            except (
                EmptyResponseError,
                Exception,
                openai.APIError,
                openai.BadRequestError,
            ) as e:
                logger.error(
                    f"erreur_modele: {conversations[i].model_name}, '{str(e)}'\n{traceback.format_exc()}",
                    extra={
                        "request": request,
                        "error": str(e),
                        "stacktrace": traceback.format_exc(),
                    },
                )
                # TODO: do that only when controller is offline
                config.outage_models.append(conversations[i].model_name)
                add_outage_model(
                    config.controller_url,
                    conversations[i].model_name,
                    reason=str(e),
                )
                # gr.Warning(
                #     duration=0,
                #     message="Erreur avec l'interrogation d'un des modèles, veuillez patienter, le comparateur trouve deux nouveaux modèles à interroger.",
                # )
                # If it's the first message in conversation, re-roll
                # TODO: need to be adapted to template logic (first messages could already have a >2 length if not zero-shot)
                if len(conversations[i].messages) < 3:

                    # TODO: refacto! class method?
                    def reset_conv_state(state, model_name=""):
                        # self.messages = get_conversation_template(model_name)
                        state.messages = []
                        state.output_tokens = None

                        # TODO: get it from api if generated
                        state.conv_id = uuid.uuid4().hex

                        # TODO: add template info? and test it
                        state.template_name = "zero_shot"
                        state.template = []
                        state.model_name = model_name
                        return state

                    app_state.awaiting_responses = False
                    config.outage_models = refresh_outage_models(
                        config.outage_models, controller_url=config.controller_url
                    )
                    # Simpler to repick 2 models
                    # app_state.model_left, app_state.model_right = get_battle_pair(
                    model_left, model_right = get_battle_pair(
                        config.models,
                        BATTLE_TARGETS,
                        config.outage_models,
                        SAMPLING_WEIGHTS,
                        SAMPLING_BOOST_MODELS,
                    )
                    conv_a = reset_conv_state(conv_a, model_name=model_left)
                    conv_b = reset_conv_state(conv_b, model_name=model_right)

                    logger.info(
                        f"selection_modeles: {model_left}, {model_right}",
                        extra={request: request},
                    )

                    app_state, conv_a, conv_b, chatbot = add_text(
                        app_state,
                        conv_a,
                        conv_b,
                        app_state.original_user_prompt,
                        request,
                    )
                    # Empty generation queue
                    gen = []
                    # continue
                    # pass

                # Case where conversation was already going on, endpoint error or context error
                # TODO: differentiate if it's just an endpoint error, in which case it can be repicked
                else:
                    # print(conversations[i].messages)
                    app_state.awaiting_responses = False
                    logger.error(
                        f"erreur_milieu_discussion: {conversations[i].model_name}, "
                        + str(e)
                    )
                    raise gr.Error(
                        duration=0,
                        message="Malheureusement, un des deux modèles a cassé ! Peut-être est-ce une erreur temporaire, ou la conversation a été trop longue. Nous travaillons pour mieux gérer ces cas.",
                    )
                    # break
            else:
                # TODO: ???
                break
        else:
            logger.critical("maximum_attempts_reached")
            raise (
                RuntimeError(
                    "Le comparateur a un problème. Veuillez réessayer plus tard."
                )
            )

        # Got answer at this point
        app_state.awaiting_responses = False

        logger.info(
            f"response_modele_a ({conv_a.model_name}): {str(conv_a.messages[-1].content)}",
            extra={"request": request},
        )
        logger.info(
            f"response_modele_b ({conv_b.model_name}): {str(conv_b.messages[-1].content)}",
            extra={"request": request},
        )
        chatbot = to_threeway_chatbot(conversations)
        conv_a = conversations[0]
        conv_b = conversations[1]
        return [app_state, conv_a, conv_b, chatbot, textbox]

    def enable_conclude(textbox):

        return {
            conclude_btn: gr.update(interactive=True),
            send_btn: gr.update(interactive=(textbox != "")),
        }

    gr.on(
        triggers=[textbox.submit, send_btn.click],
        fn=add_text,
        api_name=False,
        inputs=[app_state] + [conv_a] + [conv_b] + [textbox],
        outputs=[app_state] + [conv_a] + [conv_b] + [chatbot],
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
        # should do .success()
        # scroll_to_output=True,
        # FIXME: return of bot_response_multi couldn't set conclude_btn and send_btn :'(
    ).then(
        fn=enable_conclude, inputs=[textbox], outputs=[conclude_btn, send_btn]
    )
    # // Enable navigation prompt
    # window.onbeforeunload = function() {
    #     return true;
    # };
    # // Remove navigation prompt
    # window.onbeforeunload = null;

    def show_vote_area(request: gr.Request):
        logger.info(
            "ecran_vote",
            extra={"request": request},
        )
        return {
            # stepper_block: gr.update(
            #     value=stepper_html(
            #         "Votez pour découvrir leurs identités", 3, 4
            #     )
            # ),
            # chat_area: gr.update(visible=False),
            send_area: gr.update(visible=False),
            vote_area: gr.update(visible=True),
            buttons_footer: gr.update(visible=True),
        }

    gr.on(
        triggers=[conclude_btn.click],
        inputs=[],
        outputs=[send_area, vote_area, buttons_footer],
        api_name=False,
        fn=show_vote_area,
        # scroll_to_output=True,
        show_progress="hidden",
    ).then(
        fn=(lambda: None),
        inputs=None,
        outputs=None,
        js="""(args) => {
setTimeout(() => {
console.log("scrolling to #vote-area");
const chatArea = document.querySelector('#chat-area');
chatArea.style.paddingBottom = `0px`;
const voteArea = document.getElementById('vote-area');
voteArea.scrollIntoView({
  behavior: 'smooth',
  block: 'start'
});}, 500);
}""",
    )

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
        app_state,
        conv_a,
        conv_b,
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
            "positive_a": ",".join(positive_a_output) if positive_a_output else None,
            "positive_b": ",".join(positive_b_output) if positive_b_output else None,
            "negative_a": ",".join(negative_a_output) if negative_a_output else None,
            "negative_b": ",".join(negative_b_output) if negative_b_output else None,
            "comments_a": str(comments_a_output),
            "comments_b": str(comments_b_output),
        }
        if hasattr(app_state, "category"):
            category = app_state.category
        else:
            category = None

        vote_last_response(
            [conv_a, conv_b],
            which_model_radio_output,
            category,
            details,
            request,
        )

        model_a = get_model_extra_info(conv_a.model_name, config.models_extra_info)
        model_b = get_model_extra_info(conv_b.model_name, config.models_extra_info)
        logger.debug("output_tokens: " + str(conv_a.output_tokens))
        logger.debug("output_tokens: " + str(conv_b.output_tokens))
        # TODO: Improve fake token counter: 4 letters by token: https://genai.stackexchange.com/questions/34/how-long-is-a-token
        model_a_tokens = (
            conv_a.output_tokens
            if conv_a.output_tokens and conv_a.output_tokens != 0
            else count_output_tokens(conv_a.messages)
        )

        model_b_tokens = (
            conv_b.output_tokens
            if conv_b.output_tokens and conv_b.output_tokens != 0
            else count_output_tokens(conv_b.messages)
        )

        # TODO:
        # request_latency_a = conv_a.conv.finish_tstamp - conv_a.conv.start_tstamp
        # request_latency_b = conv_b.conv.finish_tstamp - conv_b.conv.start_tstamp
        model_a_impact = get_llm_impact(
            model_a, conv_a.model_name, model_a_tokens, None
        )
        model_b_impact = get_llm_impact(
            model_b, conv_b.model_name, model_b_tokens, None
        )

        reveal_html = build_reveal_html(
            model_a=model_a,
            model_b=model_b,
            which_model_radio=which_model_radio_output,
            model_a_impact=model_a_impact,
            model_b_impact=model_b_impact,
            model_a_tokens=model_a_tokens,
            model_b_tokens=model_b_tokens,
        )
        return {
            positive_a: gr.update(interactive=False),
            positive_b: gr.update(interactive=False),
            negative_a: gr.update(interactive=False),
            negative_b: gr.update(interactive=False),
            comments_a: gr.update(interactive=False),
            comments_b: gr.update(interactive=False),
            comments_link: gr.update(interactive=False),
            reveal_screen: gr.update(interactive=False),
            results_area: gr.update(interactive=False),
            buttons_footer: gr.update(interactive=False),
            which_model_radio: gr.update(interactive=False),
            reveal_screen: gr.update(visible=True),
            results_area: gr.update(value=reveal_html),
            buttons_footer: gr.update(visible=False),
            which_model_radio: gr.update(interactive=False),
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
