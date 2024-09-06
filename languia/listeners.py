from languia.block_arena import *
import traceback

from languia.utils import (
    stepper_html,
    get_battle_pair,
    build_reveal_html,
    vote_last_response,
    get_model_extra_info,
    count_output_tokens,
    get_llm_impact,
    # save_profile,
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
    # TODO: to import/replace State and bot_response?
    ConversationState,
    bot_response,
)


import gradio as gr


from languia.config import logger


from languia import config


# Register listeners
def register_listeners():

    # Sometimes @demo.load is not triggered!

    # Step 0

    # NOTE: part of this logic is implemented in the js loaded with the gradio demo block
    # TODO: make a cool input-output js function to pass here instead of in main js
    @demo.load(
        inputs=[],
        outputs=(conversations + [stepper_block, mode_screen]),
        api_name=False,
    )
    def enter_arena(request: gr.Request):
        # tos_accepted = accept_tos_checkbox
        # if tos_accepted:
        # logger.info(f"ToS accepted")
        # {'name': 'languia', 'msg': 'ToS accepted: fwypynv2sy', 'args': ('fwypynv2sy',), 'levelname': 'INFO', 'levelno': 20, 'pathname': '/home/hadrien/git/languia/languia/listeners.py', 'filename': 'listeners.py', 'module': 'listeners', 'exc_info': None, 'exc_text': None, 'stack_info': None, 'lineno': 64, 'funcName': 'enter_arena', 'created': 1725292327.7355227, 'msecs': 735.0, 'relativeCreated': 7554.653644561768, 'thread': 139691558962880, 'threadName': 'AnyIO worker thread', 'processName': 'SpawnProcess-4', 'process': 122874, 'request': <gradio.route_utils.Request object at 0x7f0c7ed0a550>}
        logger.info(
            # config.Log("ToS accepted: %s" % request.session_hash),
            f"ToS accepted: %s" % request.session_hash,
            extra={"request": request},
        )

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
            ConversationState(model_name=model_left),
            ConversationState(model_name=model_right),
        ]
        logger.info(
            "Picked 2 models: " + model_left + " and " + model_right,
            extra={request: request},
        )
        return conversations + [
            gr.update(visible=True),
            gr.update(visible=True),
        ]

    # Step 1

    @free_mode_btn.click(
        inputs=[],
        outputs=[free_mode_btn, send_area, mode_screen, shuffle_btn, textbox],
        api_name=False,
    )
    def free_mode(request: gr.Request):
        category = "unguided"
        app_state.category = category

        logger.info(
            f"Chose free mode",
            extra={"request": request},
        )

        return {
            free_mode_btn: gr.update(visible=False),
            send_area: gr.update(visible=True),
            mode_screen: gr.update(elem_classes="fr-container send-area-enabled"),
            shuffle_btn: gr.update(interactive=False),
            # Don't remove or autofocus won't work
            textbox: gr.skip(),
        }

    # Step 1.1
    @guided_cards.change(
        inputs=[guided_cards],
        outputs=[send_area, textbox, mode_screen, shuffle_btn, free_mode_btn],
        api_name=False,
    )
    def set_guided_prompt(guided_cards, event: gr.EventData, request: gr.Request):
        category = guided_cards
        app_state.category = category
        prompt = gen_prompt(category)
        logger.info(
            f"set_guided_prompt: {category}",
            extra={"request": request},
        )
        return [
            gr.update(visible=True),
            gr.update(value=prompt),
            # gr.update(visible=True),
            gr.update(elem_classes="fr-container send-area-enabled"),
            gr.update(interactive=True),
            gr.update(visible=False),
        ]

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

    @shuffle_btn.click(inputs=[guided_cards], outputs=[textbox], api_name=False)
    def shuffle_prompt(guided_cards):
        return gen_prompt(category=guided_cards)

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
            conversations[i].messages.append(gr.ChatMessage(role=f"user", content=text))

            if len(conversations[i].messages) == 1:
                app_state.original_user_prompt = text
                logger.debug(
                "Saving original prompt: " + app_state.original_user_prompt,
                extra={"request": request},
                )
            # Added in individual bot_message yielding function
            # # Empty assistant message is needed to be editable by yielding received text afterwards
            # conversations[i].messages.append(gr.ChatMessage(role=f"assistant", content=""))

        return (
            # 2 conversations
            conversations
            # 1 chatbot
            + [to_threeway_chatbot(conversations)]
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
            f"bot_response_multi",
            extra={"request": request},
            # Log("reponse des bots",request.session_hash),
        )

        conversations = [conversation_a, conversation_b]

        gen = []
        try:
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

            iters = 0
            while True:
                stop = True
                iters += 1
                for i in range(config.num_sides):
                    try:
                        # if iters % 30 == 1 or iters < 3:
                        ret = next(gen[i])
                        conversations[i] = ret
                        stop = False
                    except StopIteration:
                        pass

                yield conversations + [to_threeway_chatbot(conversations)]

                if stop:
                    break
        except Exception as e:
            logger.error(
                f"Problem with generating model {conversations[i].model_name}. Adding to outages list.",
                extra={"request": request, "error": str(e)},
            )
            app_state.crashed = True
            config.outage_models.append(conversations[i].model_name)
            add_outage_model(
                config.controller_url,
                conversations[i].model_name,
                # FIXME: seems equal to None always?
                reason=str(e),
            )
            logger.error(str(e), extra={"request": request})
            logger.error(traceback.format_exc(), extra={"request": request})
            # gr.Warning(
            #     message="Erreur avec le chargement d'un des modèles, veuillez recommencer une conversation",
            # )
            gr.Warning(
                duration=0,
                message="Erreur avec le chargement d'un des modèles, le comparateur va trouver deux nouveaux modèles à interroger. Veuillez poser votre question de nouveau.",
            )

            # TODO: reset arena a better way...
            chatbot = gr.Chatbot(
                # TODO:
                type="messages",
                elem_id=f"main-chatbot",
                # min_width=
                height="100%",
                # Doesn't show because it always has at least our message
                # Note: supports HTML, use it!
                placeholder="<em>Veuillez écrire au modèle</em>",
                # No difference
                # bubble_full_width=False,
                layout="panel",  # or "bubble"
                likeable=False,
                label=label,
                # UserWarning: show_label has no effect when container is False.
                show_label=False,
                container=False,
                # One can dream
                # autofocus=True,
                # autoscroll=True,
                elem_classes="chatbot",
                # Should we show it?
                show_copy_button=False,
            )

            return (conversation_a, conversation_b, chatbot)

    def goto_chatbot(
        request: gr.Request,
        #  FIXME: ignored
        api_name=False,
    ):
        # textbox
        logger.info(
            "chatbot launched",
            extra={"request": request},
        )

        return (
            [
                gr.update(
                    value="",
                    placeholder="Continuer à discuter avec les deux modèles",
                )
            ]
            # stepper_block
            + [
                gr.update(
                    value=stepper_html(
                        "Discutez avec deux modèles d'IA puis donnez votre avis sur les réponses",
                        2,
                        4,
                    )
                )
            ]
            # mode_screen
            + [gr.update(visible=False)]
            # chat_area
            + [gr.update(visible=True)]
            # send_btn
            + [gr.update(interactive=False)]
            # retry_btn
            # + [gr.update(visible=True)]
            # shuffle_btn
            + [gr.update(visible=False)]
            # conclude_btn
            + [gr.update(visible=True, interactive=False)]
        )

    def check_answers(conversation_a, conversation_b, request: gr.Request):

        logger.debug(
            "models finished answering",
            extra={"request": request},
        )
        #     # FIXME: weird way of checking if the stream never answered, openai api doesn't seem to raise anything if error in stream mode
        #     if len(data["text"].strip()) == 0:
        #         raise RuntimeError(f"No answer from API for model {model_name}")

        if hasattr(app_state, "crashed") and app_state.crashed:
            logger.error(
                    "model crash detected, keeping prompt",
                    extra={"request": request},
                )
            app_state.crashed = False
            model_left, model_right = get_battle_pair(
                    config.models,
                    BATTLE_TARGETS,
                    config.outage_models,
                    SAMPLING_WEIGHTS,
                    SAMPLING_BOOST_MODELS,
                )
            conversation_a = ConversationState(model_name=model_left)
            conversation_b = ConversationState(model_name=model_right)

            logger.info(
                "Repicked 2 models: " + model_left + " and " + model_right,
                extra={request: request},
            )
            # conversation_a = ConversationState()
            # conversation_b = ConversationState()

            logger.info(
                "prefilling opening prompt",
                extra={"request": request},
            )
            textbox.value = app_state.original_user_prompt

            return (
                [conversation_a]
                + [conversation_b]
                # chatbot
                + [[]]
                # disable conclude btn
                + [gr.update(interactive=False)]
                # + [gr.skip()]
                + [app_state.original_user_prompt]
            )

        # logger.info(
        #     "models answered with success",
        #     extra={"request": request},
        # )

        return (
            [conversation_a]
            + [conversation_b]
            + [chatbot]
            # enable conclude_btn
            + [gr.update(interactive=True)]
            # show retry_modal_btn
            # + [gr.update(visible=True)]
            + [
                gr.update(
                    value="",
                    placeholder="Continuer à discuter avec les deux modèles d'IA",
                )
            ]
        )

    gr.on(
        triggers=[textbox.submit, send_btn.click],
        fn=add_text,
        api_name=False,
        inputs=conversations + [textbox],
        outputs=conversations + [chatbot],
    ).then(
        fn=goto_chatbot,
        inputs=[],
        outputs=(
            [textbox]
            + [stepper_block]
            + [mode_screen]
            + [chat_area]
            + [send_btn]
            + [shuffle_btn]
            + [conclude_btn]
        ),
    ).then(
        # gr.on(triggers=[chatbots[0].change,chatbots[1].change],
        fn=bot_response_multi,
        inputs=conversations + [temperature, top_p, max_output_tokens],
        outputs=conversations + [chatbot],
        api_name=False,
        # should do .success()
    ).then(
        fn=check_answers,
        inputs=conversations,
        outputs=conversations + [chatbot] + [conclude_btn]
        # + [retry_modal_btn]
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
            gr.update(
                value=stepper_html(
                    "Donnez votre avis puis les deux IA vous seront dévoilées !", 3, 4
                )
            ),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(visible=True),
        ]

    @which_model_radio.change(
        inputs=[which_model_radio],
        outputs=[supervote_area, supervote_send_btn, why_vote] + supervote_sliders,
        api_name=False,
    )
    def build_supervote_area(vote_radio, request: gr.Request):
        logger.info(
            "(temporarily) voted for " + str(vote_radio),
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
    # @both_equal_link.click(inputs=[])

    @return_btn.click(
        inputs=[],
        outputs=[stepper_block] + [vote_area]
        # + [supervote_area]
        + [chat_area] + [send_area] + [buttons_footer],
    )
    def return_to_chat(
        request: gr.Request,
        #    FIXME: ignored
        api_name=False,
    ):
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
         outputs=[
            stepper_block,
            vote_area,
            supervote_area,
            feedback_row,
            results_area,
            buttons_footer,
        ],
        # outputs=[quiz_modal],
        api_name=False,
    )
    def vote_preferences(
        conversation_a,
        conversation_b,
        which_model_radio,
        relevance_slider,
        form_slider,
        style_slider,
        comments_text,
        request: gr.Request,
    ):
        details = {
            "relevance": int(relevance_slider),
            "form": int(form_slider),
            "style": int(style_slider),
            "comments": str(comments_text),
        }
        if hasattr(app_state, "category"):
            category = app_state.category
        else:
            category = None

        vote_last_response(
            [conversation_a, conversation_b],
            which_model_radio,
            category,
            details,
            request,
        )
        # quiz_modal.visible = True
        # return Modal(visible=True)

    # @send_poll_btn.click(
    #     inputs=[
    #         conversations[0],
    #         conversations[1],
    #         which_model_radio,
    #         chatbot_use,
    #         gender,
    #         age,
    #         profession,
    #     ],
    #     outputs=[
    #         quiz_modal,
    #         stepper_block,
    #         vote_area,
    #         supervote_area,
    #         feedback_row,
    #         results_area,
    #         buttons_footer,
    #     ],
    #     api_name=False,
    # )
    # @skip_poll_btn.click(
    #     inputs=[
    #         conversations[0],
    #         conversations[1],
    #         which_model_radio,
    #         chatbot_use,
    #         gender,
    #         age,
    #         profession,
    #     ],
    #     outputs=[
    #         quiz_modal,
    #         stepper_block,
    #         vote_area,
    #         supervote_area,
    #         feedback_row,
    #         results_area,
    #         buttons_footer,
    #     ],
    #     api_name=False,
    # )
    # def send_poll(
    #     conversation_a,
    #     conversation_b,
    #     which_model_radio,
    #     chatbot_use,
    #     gender,
    #     age,
    #     profession,
    #     request: gr.Request,
    #     event: gr.EventData,
    # ):
    #     confirmed = event.target.value == "Envoyer"  # Not "Passer"

    #     save_profile(
    #         conversation_a,
    #         conversation_b,
    #         which_model_radio,
    #         chatbot_use,
    #         gender,
    #         age,
    #         profession,
    #         confirmed,
    #         request,
    #     )

        model_a = get_model_extra_info(
            conversation_a.model_name, config.models_extra_info
        )
        model_b = get_model_extra_info(
            conversation_b.model_name, config.models_extra_info
        )

        # TODO: Improve fake token counter: 4 letters by token: https://genai.stackexchange.com/questions/34/how-long-is-a-token
        model_a_tokens = count_output_tokens(conversation_a.messages)
        model_b_tokens = count_output_tokens(conversation_b.messages)
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
            which_model_radio=which_model_radio,
            model_a_impact=model_a_impact,
            model_b_impact=model_b_impact,
            model_a_tokens=model_a_tokens,
            model_b_tokens=model_b_tokens,
        )
        return [
            # Modal(visible=False),
            # Comment: this is very ugly but I couldn't get the nicer method of updating named blocks to work.
            # As a ref:
            # stepper_block,
            # vote_area,
            # supervote_area,
            # feedback_row,
            # results_area,
            # buttons_footer,
            gr.update(
                value=stepper_html(
                    "Découvrez les modèles d'IA générative avec lesquels vous venez de discuter",
                    4,
                    4,
                )
            ),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(visible=True, value=reveal_html),
            gr.update(visible=False),
        ]

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
    #     # List of objects to clear
    #     outputs=conversations
    #     + [chatbot]
    #     + [textbox]
    #     + [chat_area]
    #     + [vote_area]
    #     + [supervote_area]
    #     + [mode_screen]
    #     + [retry_modal]
    #     + [conclude_btn]
    #     + [retry_modal_btn]
    #     + [shuffle_btn],
    # )

    # def clear_history(
    #     conversation_a,
    #     conversation_b,
    #     chatbot,
    #     textbox,
    #     request: gr.Request,
    # ):
    #     logger.info("clear_history", extra={request: request})
    #     #     + chatbots
    #     # + [textbox]
    #     # + [chat_area]
    #     # + [vote_area]
    #     # + [supervote_area]
    #     # + [mode_screen],
    #     config.outage_models = refresh_outage_models(
    #         config.outage_models, controller_url=config.controller_url
    #     )

    #     # app_state.model_left, app_state.model_right = get_battle_pair(
    #     model_left, model_right = get_battle_pair(
    #         config.models,
    #         BATTLE_TARGETS,
    #         config.outage_models,
    #         SAMPLING_WEIGHTS,
    #         SAMPLING_BOOST_MODELS,
    #     )
    #     conversation_a = ConversationState(model_name=model_left)
    #     conversation_b = ConversationState(model_name=model_right)
    #     logger.info(
    #         "Picked 2 models: " + model_left + " and " + model_right,
    #         extra={request: request},
    #     )
    #     return [
    #         # Conversations
    #         conversation_a,
    #         conversation_b,
    #         None,
    #         None,
    #         gr.update(value="", placeholder="Réinterrogez deux nouveaux modèles"),
    #         gr.update(visible=False),
    #         gr.update(visible=False),
    #         gr.update(visible=False),
    #         gr.update(visible=True),
    #         # retry_modal
    #         Modal(visible=False),
    #         #  conclude_btn + retry_modal_btn
    #         gr.update(visible=False),
    #         gr.update(visible=False),
    #         # shuffle_btn
    #         gr.update(visible=True),
    #     ]
