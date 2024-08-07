from languia.block_arena import *
import traceback

from languia.utils import (
    stepper_html,
    get_ip,
    get_battle_pair,
    build_reveal_html,
    header_html,
    vote_last_response,
    get_model_extra_info,
    count_output_tokens,
    get_llm_impact,
    running_eq,
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

from languia.config import logger


# Register listeners
def register_listeners():

    # Step -1
    
    # @demo.load(inputs=[], outputs=[],api_name=False)
    # def init_models(request: gr.Request):
    #     logger.info("Logged")

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
        # js?
        outputs=[
            free_mode_btn,
            guided_mode_btn,
            send_area,
            guided_area,
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
                elem_classes="fr-ml-auto " + mode_selection_classes + " selected"
            ),
            gr.update(elem_classes="fr-mr-auto " + mode_selection_classes),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(elem_classes="fr-container send-area-enabled"),
        ]

    @guided_mode_btn.click(
        inputs=[],
        outputs=[
            free_mode_btn,
            guided_mode_btn,
            # send_area,
            guided_area,
            mode_screen,
        ],
        api_name=False,
        # TODO: scroll_to_output?
    )
    def guided_mode(request: gr.Request):
        # print(guided_mode_btn.elem_classes)
        logger.info(
            f"Chose guided mode",
            extra={"request": request},
        )
        if "selected" in guided_mode_btn.elem_classes:
            return [gr.skip() * 4]
        else:
            return [
                gr.update(elem_classes="fr-ml-auto " + mode_selection_classes),
                gr.update(
                    elem_classes="fr-mr-auto " + mode_selection_classes + " selected"
                ),
                # send_area
                # gr.update(visible=False),
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
            "variete",
            "regional",
            "pedagogie",
            "creativite",
            "registre",
            "maniere",
        ]:
            preprompts = config.preprompts_table[chosen_guide]
        else:
            logger.error(
                "Type of guided prompt not listed: " + str(chosen_guide),
                extra={"request": request},
            )
        preprompt = preprompts[np.random.randint(len(preprompts))]
        return [gr.update(visible=True), gr.update(value=preprompt)]

    gr.on(
        triggers=[
            maniere.click,
            registre.click,
            regional.click,
            variete.click,
            pedagogie.click,
            creativite_btn.click,
        ],
        fn=set_guided_prompt,
        inputs=[],
        outputs=[send_area, textbox],
        api_name=False,
    )

    @textbox.change(inputs=textbox, outputs=send_btn, api_name=False)
    def change_send_btn_state(textbox):
        if textbox == "":
            return gr.update(interactive=False)
        else:
            return gr.update(interactive=True)

    def add_text(
        state0: gr.State,
        state1: gr.State,
        text: gr.Text,
        request: gr.Request,
    ):

        # TODO: add turn
        logger.info(
            f"add_text",
            # f"add_text. len: {len(text)}",
            extra={"request": request, "prompt": text},
        )
        conversations_state = [state0, state1]

        # TODO: refacto and put init apart
        # Init conversations_state if necessary
        is_conversations_state = hasattr(conversations_state[0], "model_name")
        got_battle_pair_already = False
        if is_conversations_state:
            if conversations_state[0].model_name != "":
                got_battle_pair_already = True

        if not got_battle_pair_already:
            # assert conversations_state[1] is None
            logger.info("outage_models:  " + " ".join(outage_models))
            model_left, model_right = get_battle_pair(
                config.models,
                BATTLE_TARGETS,
                outage_models,
                SAMPLING_WEIGHTS,
                SAMPLING_BOOST_MODELS,
            )
            logger.info("Picked 2 models: " + model_left + " and " + model_right)
            conversations_state = [
                # NOTE: replacement of gr.State() to ConversationState happens here
                ConversationState(model_name=model_left),
                ConversationState(model_name=model_right),
            ]
            # TODO: test here if models answer?

        model_list = [
            conversations_state[i].model_name for i in range(config.num_sides)
        ]
        # all_conv_text_left = conversations_state[0].conv.get_prompt()
        # all_conv_text_right = conversations_state[1].conv.get_prompt()
        # all_conv_text = (
        #     all_conv_text_left[-1000:] + all_conv_text_right[-1000:] + "\nuser: " + text
        # )
        # TODO: turn on moderation in battle mode
        # flagged = moderation_filter(all_conv_text, model_list, do_moderation=False)
        # if flagged:
        #     logger.info(f"violate moderation (anony). ip: {ip}. text: {text}")
        #     # overwrite the original text
        #     text = MODERATION_MSG

        # conv = conversations_state[0].conv
        # if (len(conv.messages) - conv.offset) // 2 >= CONVERSATION_TURN_LIMIT:
        #     logger.info(f"conversation turn limit. ip: {get_ip(request)}. text: {text}")
        #     for i in range(config.num_sides):
        #         conversations_state[i].skip_next = True
        #         # FIXME: fix return value
        #     return (
        #         # 2 conversations_state
        #         conversations_state
        #         # 2 chatbots
        #         + [x.to_gradio_chatbot() for x in conversations_state]
        #         # text
        #         # + [CONVERSATION_LIMIT_MSG]
        #         # + [gr.update(visible=True)]
        #     )

        text = text[:BLIND_MODE_INPUT_CHAR_LEN_LIMIT]  # Hard cut-off
        # TODO: what do?

        for i in range(config.num_sides):
            conversations_state[i].conv.append_message(
                conversations_state[i].conv.roles[0], text
            )
            # TODO: Empty assistant message is needed to show user's first question but why??
            conversations_state[i].conv.append_message(
                conversations_state[i].conv.roles[1], None
            )
            conversations_state[i].skip_next = False

        return (
            # 2 conversations_state
            conversations_state
            # 2 chatbots
            + [x.to_gradio_chatbot() for x in conversations_state]
        )

    # TODO: move this
    def bot_response_multi(
        state0,
        state1,
        temperature,
        top_p,
        max_new_tokens,
        request: gr.Request,
    ):
        logger.info(
            f"bot_response_multi: {get_ip(request)}",
            extra={"request": request},
        )

        conversations_state = [state0, state1]

        gen = []
        for i in range(config.num_sides):
            gen.append(
                bot_response(
                    conversations_state[i],
                    temperature,
                    top_p,
                    max_new_tokens,
                    request,
                    apply_rate_limit=True,
                    use_recommended_config=True,
                )
            )

        is_stream_batch = []
        for i in range(config.num_sides):
            is_stream_batch.append(
                conversations_state[i].model_name
                in [
                    "gemini-pro",
                    "gemini-pro-dev-api",
                    "gemini-1.0-pro-vision",
                    "gemini-1.5-pro",
                    "gemini-1.5-flash",
                    "gemma-1.1-2b-it",
                    "gemma-1.1-7b-it",
                ]
            )
        chatbots = [None] * config.num_sides
        iters = 0
        while True:
            stop = True
            iters += 1
            for i in range(config.num_sides):
                try:
                    # yield gemini fewer times as its chunk size is larger
                    # otherwise, gemini will stream too fast
                    if not is_stream_batch[i] or (iters % 30 == 1 or iters < 3):
                        ret = next(gen[i])
                        conversations_state[i], chatbots[i] = ret[0], ret[1]
                    stop = False
                except StopIteration:
                    pass
                except Exception as e:
                    logger.error(
                        f"Problem with generating model {conversations_state[i].model_name}. Adding to outcasts list and re-rolling.",
                        extra={"request": request},
                    )
                    outage_models.append(conversations_state[i].model_name)
                    logger.error(str(e), extra={"request": request})
                    logger.error(traceback.format_exc(), extra={"request": request})
                    gr.Warning(
                        message="Erreur avec le chargement d'un des modèles, l'arène va trouver deux nouveaux modèles à interroger. Posez votre question de nouveau.",
                    )
                    # conversations_state[0],conversations_state[1] = clear_history(
                    #     state0=conversations_state[0],
                    #     state1=conversations_state[1],
                    #     chatbot0=chatbots[0],
                    #     chatbot1=chatbots[1],
                    #     textbox=textbox,
                    #     request=request,
                    # )
                    app_state.original_user_prompt = chatbots[0][0][0]
                    logger.info(
                        "Saving original prompt: " + app_state.original_user_prompt,
                        extra={"request": request},
                    )
                    # print(str(conversations_state[0].conv_id))
                    # print(str(conversations_state[1].conv_id))
                    # Not effective:
                    # conversations_state[0],conversations_state[1], chatbots[0], chatbots[1] = gr.State(value=None), None, gr.Chatbot(value=None), ""

                    # print("conversations_state[0]:" + str(conversations_state[0].conv))
                    return (
                        state0,
                        state1,
                        chatbots[0],
                        chatbots[1],
                    )

            yield conversations_state + chatbots
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
            + [gr.update(visible=True, interactive=True)]
        )

    def check_answers(state0, state1, request: gr.Request):
        # Not set to none at all :'(
        # print(str(state0.conv_id))
        # print(str(state1.conv_id))
        logger.debug(
            "models finished answering",
            extra={"request": request},
        )

        if hasattr(app_state, "original_user_prompt"):
            if app_state.original_user_prompt != False:
                logger.info(
                    "model crash detected, keeping prompt",
                    extra={"request": request},
                )
                original_user_prompt = app_state.original_user_prompt
                app_state.original_user_prompt = False
                # TODO: reroll here
                state0 = gr.State()
                state1 = gr.State()
                # state0 = ConversationState()
                # state1 = ConversationState()

                logger.info(
                    "submitting original prompt",
                    extra={"request": request},
                )
                textbox.value = original_user_prompt

                logger.info(
                    "original prompt sent",
                    extra={"request": request},
                )
                return (
                    [state0]
                    + [state1]
                    # chatbots
                    + [""]
                    + [""]
                    # disable conclude btn
                    + [gr.update(interactive=False)]
                    + [original_user_prompt]
                )

        # enable conclude_btn
        # TODO: log answers here?
        logger.info(
            "models answered with success",
            extra={"request": request},
        )

        extra = ({"request": request},)
        return (
            [state0]
            + [state1]
            + chatbots
            + [gr.update(interactive=True)]
            + [textbox]
        )

    gr.on(
        triggers=[textbox.submit, send_btn.click],
        fn=add_text,
        api_name=False,
        inputs=conversations_state + [textbox],
        # inputs=conversations_state + model_selectors + [textbox],
        outputs=conversations_state + chatbots,
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
        inputs=conversations_state + [temperature, top_p, max_output_tokens],
        outputs=conversations_state + chatbots,
        api_name=False,
        # should do .success()
    ).then(
        fn=check_answers,
        inputs=conversations_state,
        outputs=conversations_state + chatbots + [conclude_btn] + [textbox],
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
            final_send_btn,
        ],
        api_name=False,
    )
    def build_supervote_area(vote_radio, request: gr.Request):
        logger.info(
            "voted for " + str(vote_radio),
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

    @final_send_btn.click(
        inputs=(
            [conversations_state[0]]
            + [conversations_state[1]]
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
        api_name=False,
    )
    def vote_preferences(
        state0,
        state1,
        which_model_radio,
        ressenti_checkbox,
        pertinence_checkbox,
        comprehension_checkbox,
        originalite_checkbox,
        comments_text,
        request: gr.Request,
    ):
        # conversations_state = [state0, state1]

        details = {
            "chosen_model": which_model_radio,
            "ressenti": ressenti_checkbox,
            "pertinence": pertinence_checkbox,
            "comprehension": comprehension_checkbox,
            "originalite": originalite_checkbox,
            "comments": comments_text,
        }
        if which_model_radio in ["bothbad", "leftvote", "rightvote"]:

            vote_last_response(
                [state0, state1],
                which_model_radio,
                details,
                request,
            )
        else:
            logger.error(
                'Model selection was neither "bothbad", "leftvote" or "rightvote", got: '
                + str(which_model_radio)
            )

        model_a = get_model_extra_info(state0.model_name, config.models_extra_info)
        model_b = get_model_extra_info(state1.model_name, config.models_extra_info)

        # TODO: Improve fake token counter: 4 letters by token: https://genai.stackexchange.com/questions/34/how-long-is-a-token
        model_a_tokens = count_output_tokens(state0.conv.roles, state0.conv.messages)
        model_b_tokens = count_output_tokens(state1.conv.roles, state1.conv.messages)
        # TODO:
        # request_latency_a = state0.conv.finish_tstamp - state0.conv.start_tstamp
        # request_latency_b = state1.conv.finish_tstamp - state1.conv.start_tstamp
        model_a_impact = get_llm_impact(
            model_a, state0.model_name, model_a_tokens, None
        )
        model_b_impact = get_llm_impact(
            model_b, state1.model_name, model_b_tokens, None
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
            gr.update(value=stepper_html("Révélation des modèles", 4, 4)),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(visible=True, value=reveal_html),
            gr.update(visible=False),
        ]

    # On reset go to mode selection mode_screen
    # gr.on(
    #     triggers=[retry_btn.click],
    #     api_name=False,
    #     # triggers=[clear_btn.click, retry_btn.click],
    #     fn=clear_history,
    #     inputs=conversations_state + chatbots + [textbox],
    #     # inputs=conversations_state + chatbots + model_selectors + [textbox],
    #     # List of objects to clear
    #     outputs=conversations_state + chatbots
    #     # + model_selectors
    #     + [textbox] + [chat_area] + [vote_area] + [supervote_area] + [mode_screen],
    # )


# def clear_history(
#     state0,
#     state1,
#     chatbot0,
#     chatbot1,
#     textbox,
#     request: gr.Request,
# ):
#     logger.info(f"clear_history (anony). ip: {get_ip(request)}")
#     #     + chatbots
#     # + [textbox]
#     # + [chat_area]
#     # + [vote_area]
#     # + [supervote_area]
#     # + [mode_screen],
#     return [
#         None,
#         None,
#         None,
#         None,
#         "",
#         gr.update(visible=False),
#         gr.update(visible=False),
#         gr.update(visible=False),
#         gr.update(visible=True),
#     ]
