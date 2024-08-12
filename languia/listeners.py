from languia.block_arena import *
import traceback

from languia.utils import (
    stepper_html,
    get_ip,
    get_battle_pair,
    build_reveal_html,
    header_html,
    vote_last_response,
    get_final_vote,
    get_model_extra_info,
    count_output_tokens,
    get_llm_impact,
    running_eq,
    log_poll,
    get_chosen_model,
    refresh_outage_models,
    add_outage_model
)

from languia.config import (
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    SAMPLING_WEIGHTS,
    BATTLE_TARGETS,
    SAMPLING_BOOST_MODELS,
    outage_models,
)

import numpy as np

# from fastchat.model.model_adapter import get_conversation_template

from languia.block_conversation import (
    # TODO: to import/replace State and bot_response?
    ConversationState,
    bot_response,
)


import gradio as gr


from languia.config import logger


from languia import config


# Register listeners
def register_listeners():

    # Step -1
    @demo.load(inputs=[], outputs=conversations, api_name=False)
    def init_models(request: gr.Request):
        outage_models = refresh_outage_models(controller_url=config.controller_url)
        # app_state.model_left, app_state.model_right = get_battle_pair(
        model_left, model_right = get_battle_pair(
            config.models,
            BATTLE_TARGETS,
            outage_models,
            SAMPLING_WEIGHTS,
            SAMPLING_BOOST_MODELS,
        )
        conversations = [
            # NOTE: replacement of gr.State() to ConversationState happens here
            ConversationState(model_name=model_left),
            ConversationState(model_name=model_right),
        ]
        logger.info(
            "Picked 2 models: " + model_left + " and " + model_right,
            extra={request: request},
        )

        return conversations

    # Step 0

    # NOTE: part of this logic is implemented in the js loaded with the gradio demo block
    # TODO: make a cool input-output js function to pass here instead of in main js
    @start_arena_btn.click(
        inputs=[],
        outputs=[header, start_screen, stepper_block, mode_screen],
        api_name=False,
    )
    def enter_arena(request: gr.Request):
        # tos_accepted = accept_tos_checkbox
        # if tos_accepted:
        # logger.info(f"ToS accepted")
        logger.info(
            f"ToS accepted",
            extra={"request": request},
        )
        return (
            gr.HTML(header_html),
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(visible=True),
        )

    # Step 1

    @free_mode_btn.click(
        inputs=[],
        outputs=[
            free_mode_btn,
            send_area,
            mode_screen,
        ],
        api_name=False,
    )
    def free_mode(request: gr.Request):
        logger.info(
            f"Chose free mode",
            extra={"request": request},
        )

        return [
            gr.update(
                elem_classes="selected"
            ),
            gr.update(visible=True),
            gr.update(elem_classes="fr-container send-area-enabled"),
        ]


    # Step 1.1

    def set_guided_prompt(event: gr.EventData, request: gr.Request):
        chosen_guide = event.target.value
        logger.info(
            f"set_guided_prompt: {chosen_guide}",
            extra={"request": request},
        )
        if chosen_guide in [
            "expression",
            "langues",
            "conseils",
            "loisirs",
            "administratif",
            "vie-professionnelle",
        ]:
            preprompts = config.preprompts_table[chosen_guide]
        else:
            logger.error(
                "Type of guided prompt not listed: " + str(chosen_guide),
                extra={"request": request},
            )
        preprompt = preprompts[np.random.randint(len(preprompts))]
        return [gr.update(visible=True), gr.update(value=preprompt)]
                            # gr.update(visible=True),
                            # gr.update(elem_classes="fr-container send-area-enabled"),

    gr.on(
        triggers=[
            # expression.click,
            langues.click,
            conseils.click,
            loisirs.click,
            administratif.click,
            # vie_professionnelle.click,
        ],
        fn=set_guided_prompt,
        inputs=[],
        outputs=[send_area, textbox],
        api_name=False,
    )
        # .then(
        #         js="""
        # () =>
        # {
        #     console.log("rerolling");

        #   const targetElement = document.getElementById('guided-area');
        #     targetElement.scrollIntoView({
        #       behavior: 'smooth'
        #     });
        #   }
        # """)

    @textbox.change(inputs=textbox, outputs=send_btn, api_name=False)
    def change_send_btn_state(textbox):
        if textbox == "":
            return gr.update(interactive=False)
        else:
            return gr.update(interactive=True)

    def add_text(
        conversation_a: gr.State,
        conversation_b: gr.State,
        text: gr.Text,
        request: gr.Request,
    ):

        # TODO: add turn
        logger.info(
            f"add_text",
            # f"add_text. len: {len(text)}",
            extra={"request": request, "prompt": text},
        )
        conversations = [conversation_a, conversation_b]

        model_list = [conversations[i].model_name for i in range(config.num_sides)]

        # FIXME: turn on moderation in battle mode
        # flagged = moderation_filter(all_conv_text, model_list, do_moderation=False)
        # if flagged:
        #     logger.info(f"violate moderation (anony). ip: {ip}. text: {text}")
        #     # overwrite the original text
        #     text = MODERATION_MSG

        # FIXME:  CONVERSATION_TURN_LIMIT:
        #     logger.info(f"conversation turn limit. ip: {get_ip(request)}. text: {text}")

        text = text[:BLIND_MODE_INPUT_CHAR_LEN_LIMIT]  # Hard cut-off
        # TODO: what do?

        for i in range(config.num_sides):
            conversations[i].conv.append_message(conversations[i].conv.roles[0], text)
            # TODO: Empty assistant message is needed to show user's first question but why??
            conversations[i].conv.append_message(conversations[i].conv.roles[1], None)
            conversations[i].skip_next = False

        return (
            # 2 conversations
            conversations
            # 2 chatbots
            + [x.to_gradio_chatbot() for x in conversations]
        )

    # TODO: move this
    def bot_response_multi(
        conversation_a,
        conversation_b,
        temperature,
        top_p,
        max_new_tokens,
        request: gr.Request,
    ):
        logger.info(
            f"bot_response_multi: {get_ip(request)}",
            extra={"request": request},
        )

        conversations = [conversation_a, conversation_b]

        gen = []
        for i in range(config.num_sides):
            gen.append(
                bot_response(
                    conversations[i],
                    temperature,
                    top_p,
                    max_new_tokens,
                    request,
                    apply_rate_limit=True,
                    use_recommended_config=True,
                )
            )

        chatbots = [None] * config.num_sides
        iters = 0
        while True:
            stop = True
            iters += 1
            for i in range(config.num_sides):
                try:
                    if (iters % 30 == 1 or iters < 3):
                        ret = next(gen[i])
                        conversations[i], chatbots[i] = ret[0], ret[1]
                    stop = False
                except StopIteration:
                    pass
                except Exception as e:
                    logger.error(
                        f"Problem with generating model {conversations[i].model_name}. Adding to outages list.",
                        extra={"request": request},
                    )
                    outage_models.append(conversations[i].model_name)
                    add_outage_model(config.controller_url, conversations[i].model_name)
                    logger.error(str(e), extra={"request": request})
                    logger.error(traceback.format_exc(), extra={"request": request})
                    gr.Warning(
                        message="Erreur avec le chargement d'un des modèles, veuillez relancer l'arène",
                    )
                    # gr.Warning(
                    #     message="Erreur avec le chargement d'un des modèles, l'arène va trouver deux nouveaux modèles à interroger. Posez votre question de nouveau.",
                    # )
                    # app_state.original_user_prompt = chatbots[0][0][0]
                    # logger.info(
                    #     "Saving original prompt: " + app_state.original_user_prompt,
                    #     extra={"request": request},
                    # )

                    return (
                        conversation_a,
                        conversation_b,
                        chatbots[0],
                        chatbots[1],
                    )

            yield conversations + chatbots
            if stop:
                break

    def goto_chatbot(request: gr.Request):
        # textbox
        logger.info(
            "chatbot launched",
            extra={"request": request},
        )

        # FIXME: tant que les 2 modèles n'ont pas répondu, le bouton "envoyer" est aussi inaccessible
        return (
            [
                gr.update(
                    value="",
                    placeholder="Continuer à discuter avec les deux modèles",
                )
            ]
            # stepper_block
            + [gr.update(value=stepper_html("Discussion avec les modèles", 2, 4))]
            # mode_screen
            + [gr.update(visible=False)]
            # chat_area
            + [gr.update(visible=True)]
            # send_btn
            + [gr.update(interactive=False)]
            # retry_btn
            # + [gr.update(visible=True)]
            # conclude_btn
            + [gr.update(visible=True, interactive=False)]
        )

    def check_answers(conversation_a, conversation_b, request: gr.Request):

        logger.debug(
            "models finished answering",
            extra={"request": request},
        )

        # if hasattr(app_state, "original_user_prompt"):
        #     if app_state.original_user_prompt != False:
        #         logger.info(
        #             "model crash detected, keeping prompt",
        #             extra={"request": request},
        #         )
        #         original_user_prompt = app_state.original_user_prompt
        #         app_state.original_user_prompt = False
        #         # TODO: reroll here
        #         conversation_a = gr.State()
        #         conversation_b = gr.State()
        #         # conversation_a = ConversationState()
        #         # conversation_b = ConversationState()

        #         logger.info(
        #             "submitting original prompt",
        #             extra={"request": request},
        #         )
        #         textbox.value = original_user_prompt

        #         logger.info(
        #             "original prompt sent",
        #             extra={"request": request},
        #         )
        #         return (
        #             [conversation_a]
        #             + [conversation_b]
        #             # chatbots
        #             + [""]
        #             + [""]
        #             # disable conclude btn
        #             + [gr.update(interactive=False)]
        #             + [original_user_prompt]
        #         )

        # logger.info(
        #     "models answered with success",
        #     extra={"request": request},
        # )

        # enable conclude_btn
        # show retry_btn
        return (
            [conversation_a]
            + [conversation_b]
            + chatbots
            + [gr.update(interactive=True)]
            + [gr.update(visible=True)]
            + [
                gr.update(
                    value="",
                    placeholder="Continuer à discuter avec les deux modèles",
                )
            ]
        )

    gr.on(
        triggers=[textbox.submit, send_btn.click],
        fn=add_text,
        api_name=False,
        inputs=conversations + [textbox],
        outputs=conversations + chatbots,
    ).then(
        fn=goto_chatbot,
        inputs=[],
        outputs=(
            [textbox]
            + [stepper_block]
            + [mode_screen]
            + [chat_area]
            + [send_btn]
            # + [retry_btn]
            + [conclude_btn]
        ),
    ).then(
        fn=bot_response_multi,
        inputs=conversations + [temperature, top_p, max_output_tokens],
        outputs=conversations + chatbots,
        api_name=False,
        # should do .success()
    ).then(
        fn=check_answers,
        inputs=conversations,
        outputs=conversations
        + chatbots
        + [conclude_btn]
        + [retry_modal_btn]
        + [textbox],
        api_name=False,
    )
    # ).then(fn=(lambda *x:x), inputs=[], outputs=[], js="""(args) => {
    #         console.log("rerolling");
    #         document.getElementById('send-btn').click();
    #         return args;
    #     }""")

    # // Enable navigation prompt
    # window.onbeforeunload = function() {
    #     return true;
    # };
    # // Remove navigation prompt
    # window.onbeforeunload = null;

    @conclude_btn.click(
        inputs=[],
        outputs=[stepper_block, chat_area, send_area, vote_area, buttons_footer],
        api_name=False,
        # TODO: scroll_to_output?
    )
    def show_vote_area(request: gr.Request):
        logger.info(
            "advancing to vote area",
            extra={"request": request},
        )
        # return {
        #     conclude_area: gr.update(visible=False),
        #     chat_area: gr.update(visible=False),
        #     send_area: gr.update(visible=False),
        #     vote_area: gr.update(visible=True),
        # }
        # [conclude_area, chat_area, send_area, vote_area]
        return [
            gr.update(value=stepper_html("Évaluation des modèles", 3, 4)),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(visible=True),
        ]

    @which_model_radio.change(
        inputs=[which_model_radio],
        outputs=[
            supervote_area,
            supervote_send_btn,
        ],
        api_name=False,
    )
    def build_supervote_area(vote_radio, request: gr.Request):
        logger.info(
            "(temporarily) voted for " + str(vote_radio),
            extra={"request": request},
        )
        return (
            gr.update(visible=True),
            gr.update(interactive=True),
        )

    # Step 3

    @return_btn.click(
        inputs=[],
        outputs=[stepper_block] + [vote_area]
        # + [supervote_area]
        + [chat_area] + [send_area] + [buttons_footer],
    )
    def return_to_chat(request: gr.Request):
        logger.info(
            "clicked return",
            extra={"request": request},
        )
        return (
            [gr.update(value=stepper_html("Discussion avec les modèles", 2, 4))]
            # vote_area
            + [gr.update(visible=False)]
            # supervote_area
            # + [gr.update(visible=False)]
            # chat_area
            + [gr.update(visible=True)]
            # send_area
            + [gr.update(visible=True)]
            # buttons_footer
            + [gr.update(visible=False)]
        )
    
    @supervote_send_btn.click(
        inputs=(
            [conversations[0]]
            + [conversations[1]]
            + [which_model_radio]
            + (supervote_sliders)
            + [comments_text]
        ),
        # outputs=[],
        outputs=[quiz_modal],
        api_name=False,
    )
    def vote_preferences(
        conversation_a,
        conversation_b,
        which_model_radio,
        relevance_slider,
        clearness_slider,
        style_slider,
        comments_text,
        request: gr.Request,
    ):
        # conversations = [conversation_a, conversation_b]
        chosen_model = get_chosen_model(which_model_radio)
        final_vote = get_final_vote(which_model_radio)
        details = {
            "model_left": conversation_a.model_name,
            "model_right": conversation_b.model_name,
            "chosen_model": chosen_model,
            "final_vote": final_vote,
            "relevance": relevance_slider,
            "clearness": clearness_slider,
            "style": style_slider,
            "comments": comments_text,
        }
        # FIXME: check input, sanitize it?
        vote_last_response(
            [conversation_a, conversation_b],
            chosen_model,
            final_vote,
            details,
            request,
        )
        # quiz_modal.visible = True
        return Modal(visible=True)

    @send_poll_btn.click(
        inputs=[
            conversations[0],
            conversations[1],
            which_model_radio,
            chatbot_use,
            gender,
            age,
            profession,
        ],
        outputs=[
            quiz_modal,
            stepper_block,
            vote_area,
            supervote_area,
            feedback_row,
            results_area,
            buttons_footer,
        ],
    )
    @skip_poll_btn.click(
        inputs=[
            conversations[0],
            conversations[1],
            which_model_radio,
            chatbot_use,
            gender,
            age,
            profession,
        ],
        outputs=[
            quiz_modal,
            stepper_block,
            vote_area,
            supervote_area,
            feedback_row,
            results_area,
            buttons_footer,
        ],
    )
    def send_poll(
        conversation_a,
        conversation_b,
        which_model_radio,
        chatbot_use,
        gender,
        age,
        profession,
        request: gr.Request,
    ):

        # FIXME: check input, sanitize it?
        log_poll(
            conversation_a,
            conversation_b,
            which_model_radio,
            chatbot_use,
            gender,
            age,
            profession,
            request,
        )

        model_a = get_model_extra_info(
            conversation_a.model_name, config.models_extra_info
        )
        model_b = get_model_extra_info(
            conversation_b.model_name, config.models_extra_info
        )

        # TODO: Improve fake token counter: 4 letters by token: https://genai.stackexchange.com/questions/34/how-long-is-a-token
        model_a_tokens = count_output_tokens(
            conversation_a.conv.roles, conversation_a.conv.messages
        )
        model_b_tokens = count_output_tokens(
            conversation_b.conv.roles, conversation_b.conv.messages
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

        model_a_running_eq = running_eq(model_a_impact)
        model_b_running_eq = running_eq(model_b_impact)

        reveal_html = build_reveal_html(
            model_a=model_a,
            model_b=model_b,
            which_model_radio=which_model_radio,
            model_a_impact=model_a_impact,
            model_b_impact=model_b_impact,
            model_a_running_eq=model_a_running_eq,
            model_b_running_eq=model_b_running_eq,
        )
        return [
            Modal(visible=False),
            gr.update(value=stepper_html("Révélation des modèles", 4, 4)),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(visible=True, value=reveal_html),
            gr.update(visible=False),
        ]

    gr.on(
        triggers=retry_modal_btn.click,
        fn=(lambda: Modal(visible=True)),
        inputs=[],
        outputs=retry_modal,
    )
    gr.on(
        triggers=close_retry_modal_btn.click,
        fn=(lambda: Modal(visible=False)),
        inputs=[],
        outputs=retry_modal,
    )

    # On reset go to mode selection mode_screen

    def clear_history(
        conversation_a,
        conversation_b,
        chatbot0,
        chatbot1,
        textbox,
        request: gr.Request,
    ):
        logger.info(f"clear_history (anony). ip: {get_ip(request)}")
        #     + chatbots
        # + [textbox]
        # + [chat_area]
        # + [vote_area]
        # + [supervote_area]
        # + [mode_screen],
        outage_models = refresh_outage_models(controller_url=config.controller_url)

        # app_state.model_left, app_state.model_right = get_battle_pair(
        model_left, model_right = get_battle_pair(
            config.models,
            BATTLE_TARGETS,
            outage_models,
            SAMPLING_WEIGHTS,
            SAMPLING_BOOST_MODELS,
        )
        conversation_a = ConversationState(model_name=model_left)
        conversation_b = ConversationState(model_name=model_right)
        logger.info(
            "Picked 2 models: " + model_left + " and " + model_right,
            extra={request: request},
        )
        return [
            # Conversations
            conversation_a,
            conversation_b,
            None,
            None,
            gr.update(value="", placeholder="Réinterrogez deux nouveaux modèles"),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=True),
            # retry_modal
            Modal(visible=False),
            #  conclude_btn + retry_modal_btn
            gr.update(visible=False),
            gr.update(visible=False),
        ]

    gr.on(
        triggers=[retry_btn.click],
        api_name=False,
        # triggers=[clear_btn.click, retry_btn.click],
        fn=clear_history,
        inputs=conversations + chatbots + [textbox],
        # List of objects to clear
        outputs=conversations
        + chatbots
        + [textbox]
        + [chat_area]
        + [vote_area]
        + [supervote_area]
        + [mode_screen]
        + [retry_modal]
        + [conclude_btn]
        + [retry_modal_btn],
    )
