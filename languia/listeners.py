from languia.block_arena import *
import traceback

from languia.utils import (
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
)

from languia.config import (
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    SAMPLING_WEIGHTS,
    BATTLE_TARGETS,
    SAMPLING_BOOST_MODELS,
)

# from fastchat.model.model_adapter import get_conversation_template

from languia.block_conversation import (
    set_conv_state,
    bot_response,
)


import gradio as gr


from languia.config import logger


from languia import config


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
    conversations = [
        # NOTE: replacement of gr.State() to ConversationState happens here
        set_conv_state(conversations[0], model_name=model_left),
        set_conv_state(conversations[1], model_name=model_right),
    ]
    logger.info(
        f"selection_modeles: {model_left}, {model_right}",
        extra={request: request},
    )
    return conversations


# Register listeners
def register_listeners():

    # Step 0

    @demo.load(
        inputs=[], outputs=(conversations), api_name=False, show_progress="hidden"
    )
    def enter_arena(request: gr.Request):
        # TODO: actually check for it
        # tos_accepted = request...
        # if tos_accepted:
        logger.info(
            "init_arene",
            extra={"request": request},
        )
        conversations = init_conversations([conv_a, conv_b], request)
        return conversations

    # Step 1

    # Step 1.1
    @guided_cards.change(
        inputs=[guided_cards],
        outputs=[send_btn, send_area, textbox, shuffle_link],
        api_name=False,
        show_progress="hidden",
    )
    def set_guided_prompt(guided_cards, event: gr.EventData, request: gr.Request):
        category = guided_cards
        app_state.category = category
        prompt = gen_prompt(category)
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
        prompt = gen_prompt(category=guided_cards)
        logger.info(
            f"shuffle: {prompt}",
            extra={"request": request},
        )
        return prompt

    @textbox.change(
        inputs=textbox, outputs=send_btn, api_name=False, show_progress="hidden"
    )
    def change_send_btn_state(textbox):
        if textbox == "" or (
            hasattr(app_state, "awaiting_responses") and app_state.awaiting_responses
        ):
            return gr.update(interactive=False)
        else:
            return gr.update(interactive=True)

    def add_text(
        conversation_a: gr.State,
        conversation_b: gr.State,
        text: gr.Text,
        request: gr.Request,
    ):

        conversations = [conversation_a, conversation_b]

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
        app_state.awaiting_responses = True
        return (
            # 2 conversations
            conversations
            # 1 chatbot
            + [to_threeway_chatbot(conversations)]
        )

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
        conversation_a,
        conversation_b,
        textbox_output,
        request: gr.Request,
    ):
        conversations = [conversation_a, conversation_b]

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
                        except StopIteration:
                            pass
                        # TODO: timeout problems on scaleway Ampere models?
                        # except httpcore.ReadTimeout:
                        #     pass
                        # except httpx.ReadTimeout:
                        #     pass

                    yield {
                        chatbot: to_threeway_chatbot(conversations),
                        # enable conclude_btn
                        conclude_btn: gr.skip(),
                        # enable send_btn if textbox not empty
                        send_btn: gr.skip(),
                        textbox: gr.skip(),
                    }
                    if stop:
                        break
            except Exception as e:
                logger.error(
                    f"erreur_modele: {conversations[i].model_name}, '{str(e)}'",
                    extra={
                        "request": request,
                        "error": str(e),
                        "stacktrace": traceback.format_exc(),
                    },
                )
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

                # Simpler to repick 2 models
                conversations = init_conversations(conversations, request)

                conversation_a, conversation_b, chatbot_output = add_text(
                    conversations[0],
                    conversations[1],
                    app_state.original_user_prompt,
                    request
                )
                # Save it to conversations
                conversations = [conversation_a, conversation_b]

                # Empty generation queue
                gen = []
            else:
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
            f"response_modele_a ({conversation_a.model_name}): {str(conversation_a.messages[-1].content)}",
            extra={"request": request},
        )
        logger.info(
            f"response_modele_b ({conversation_b.model_name}): {str(conversation_b.messages[-1].content)}",
            extra={"request": request},
        )
        chatbot_output = to_threeway_chatbot(conversations)
        return {
            chatbot: chatbot_output,
            # enable conclude_btn
            conclude_btn: gr.update(interactive=True),
            # enable send_btn if textbox not empty
            send_btn: gr.update(interactive=(textbox != "")),
            textbox: gr.skip(),
        }

    def enable_conclude():
        return {conclude_btn: gr.update(interactive=True)}

    gr.on(
        triggers=[textbox.submit, send_btn.click],
        fn=add_text,
        api_name=False,
        inputs=conversations + [textbox],
        outputs=conversations + [chatbot],
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
        inputs=conversations + [textbox],
        outputs=[chatbot, conclude_btn, send_btn, textbox],
        api_name=False,
        show_progress="hidden",
        # should do .success()
        # scroll_to_output=True,
        # FIXME: return of bot_response_multi couldn't set conclude_btn and send_btn :'(
    ).then(
        fn=enable_conclude, inputs=[], outputs=[conclude_btn]
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
        outputs=[supervote_area, supervote_send_btn, why_vote] + supervote_sliders,
        api_name=False,
        show_progress="hidden",
    )
    def build_supervote_area(vote_radio, request: gr.Request):
        logger.info(
            "vote_selection_temp:" + str(vote_radio),
            extra={"request": request},
        )
        if hasattr(app_state, "selected_model"):
            if (app_state.selected_model == "model-b" and vote_radio == "model-a") or (
                app_state.selected_model == "model-a" and vote_radio == "model-b"
            ):
                # FIXME: creates a CSS display bug  where value isn't refreshed
                new_supervote_sliders = [
                    gr.update(value=3) for slider in supervote_sliders
                ]
            else:
                new_supervote_sliders = [gr.skip() for slider in supervote_sliders]
        else:
            new_supervote_sliders = [gr.skip() for slider in supervote_sliders]

        app_state.selected_model = vote_radio
        if vote_radio == "model-a":
            why_text = """<h4>Pourquoi préférez-vous le modèle A ?</h4><p class="text-grey">Attribuez pour chaque question une note entre 1 et 5 sur le modèle A</p>"""
        elif vote_radio == "model-b":
            why_text = """<h4>Pourquoi préférez-vous le modèle B ?</h4><p class="text-grey">Attribuez pour chaque question une note entre 1 et 5 sur le modèle B</p>"""
        return [
            gr.update(visible=True),
            gr.update(interactive=True),
            gr.update(value=why_text),
        ] + new_supervote_sliders

    # Step 3

    def vote_preferences(
        conversation_a,
        conversation_b,
        which_model_radio_output,
        relevance_slider_output,
        form_slider_output,
        style_slider_output,
        comments_text_output,
        request: gr.Request,
    ):
        details = {
            "relevance": int(relevance_slider_output),
            "form": int(form_slider_output),
            "style": int(style_slider_output),
            "comments": str(comments_text_output),
        }
        if hasattr(app_state, "category"):
            category = app_state.category
        else:
            category = None

        vote_last_response(
            [conversation_a, conversation_b],
            which_model_radio_output,
            category,
            details,
            request,
        )

        model_a = get_model_extra_info(
            conversation_a.model_name, config.models_extra_info
        )
        model_b = get_model_extra_info(
            conversation_b.model_name, config.models_extra_info
        )
        logger.debug("output_tokens: " + str(conversation_a.output_tokens))
        logger.debug("output_tokens: " + str(conversation_b.output_tokens))
        # TODO: Improve fake token counter: 4 letters by token: https://genai.stackexchange.com/questions/34/how-long-is-a-token
        model_a_tokens = (
            conversation_a.output_tokens
            if conversation_a.output_tokens and conversation_a.output_tokens != 0
            else count_output_tokens(conversation_a.messages)
        )

        model_b_tokens = (
            conversation_b.output_tokens
            if conversation_b.output_tokens and conversation_b.output_tokens != 0
            else count_output_tokens(conversation_b.messages)
        )

        # TODO:
        # request_latency_a = conversation_a.conv.finish_tstamp - conversation_a.conv.start_tstamp
        # request_latency_b = conversation_b.conv.finish_tstamp - conversation_b.conv.start_tstamp
        model_a_impact = get_llm_impact(
            model_a, conversation_a.model_name, model_a_tokens, None
        )
        model_b_impact = get_llm_impact(
            model_b, conversation_b.model_name, model_b_tokens, None
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
            relevance_slider: gr.update(interactive=False),
            form_slider: gr.update(interactive=False),
            style_slider: gr.update(interactive=False),
            comments_text: gr.update(interactive=False),
            reveal_screen: gr.update(visible=True),
            results_area: gr.update(value=reveal_html),
            buttons_footer: gr.update(visible=False),
            which_model_radio: gr.update(interactive=False),
            both_equal_link: gr.update(interactive=False),
        }

    gr.on(
        triggers=[supervote_send_btn.click, both_equal_link.click],
        fn=vote_preferences,
        inputs=(
            [conversations[0]]
            + [conversations[1]]
            + [which_model_radio]
            + (supervote_sliders)
            + [comments_text]
        ),
        outputs=[
            relevance_slider,
            form_slider,
            style_slider,
            comments_text,
            reveal_screen,
            results_area,
            buttons_footer,
            which_model_radio,
            both_equal_link,
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
