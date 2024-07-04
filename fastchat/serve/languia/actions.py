import gradio as gr

import time

import json

from fastchat.serve.languia.block_conversation import get_conv_log_filename, get_ip

from fastchat.serve.remote_logger import get_remote_logger

from fastchat.utils import (
    build_logger,
    # moderation_filter,
)

logger = build_logger("gradio_web_server_multi", "gradio_web_server_multi.log")


def vote_last_response(
    conversations_state,
    vote_type,
    # _model_selectors,
    details: [],
    request: gr.Request,
):
    logger.info(f"{vote_type}_vote (anony). ip: {get_ip(request)}")
    details_str = json.dumps(details)
    logger.info(f"details: {details_str}")

    with open(get_conv_log_filename(), "a") as fout:
        data = {
            "tstamp": round(time.time(), 4),
            "type": vote_type,
            "models": [x.model_name for x in conversations_state],
            "conversations_state": [x.dict() for x in conversations_state],
            "ip": get_ip(request),
        }
        if details != []:
            data.update(details=details),
        logger.info(json.dumps(data))
        fout.write(json.dumps(data) + "\n")

    get_remote_logger().log(data)

    # names = (
    #     "### Model A: " + conversations_state[0].model_name,
    #     "### Model B: " + conversations_state[1].model_name,
    # )
    return data
    # yield names + ("",)




accept_tos_js = """
function () {
  document.cookie="languia_tos_accepted=1"
}
"""
