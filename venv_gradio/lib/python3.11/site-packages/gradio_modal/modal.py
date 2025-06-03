from __future__ import annotations

from gradio_client.documentation import document, set_documentation_group

from gradio.blocks import BlockContext
from gradio.context import Context
from gradio.component_meta import ComponentMeta
from gradio.events import Events

set_documentation_group("layout")


@document()
class Modal(BlockContext, metaclass=ComponentMeta):
    """
    Modal is a layout element within Blocks that will show its content in a popup above other content.
    Example:
        from gradio_modal import Modal
        with gr.Blocks() as demo:
            with Modal():
                text1 = gr.Textbox()
                text2 = gr.Textbox()
                btn = gr.Button("Button")
    Guides: controlling-layout
    """

    EVENTS = [Events.blur]

    def __init__(
        self,
        *,
        visible: bool = False,
        elem_id: str | None = None,
        elem_classes: list[str] | str | None = None,
        allow_user_close: bool = True,
        render: bool = True,
    ):
        """
        Parameters:
            visible: If False, modal will be hidden.
            elem_id: An optional string that is assigned as the id of this component in the HTML DOM. Can be used for targeting CSS styles.
            elem_classes: An optional string or list of strings that are assigned as the class of this component in the HTML DOM. Can be used for targeting CSS styles.
            allow_user_close: If True, user can close the modal (by clicking outside, clicking the X, or the escape key).
            render: If False, component will not render be rendered in the Blocks context. Should be used if the intention is to assign event listeners now but render the component later.
        """
        self.allow_user_close = allow_user_close
        BlockContext.__init__(
            self,
            visible=visible,
            elem_id=elem_id,
            elem_classes=elem_classes,
            render=render,
        )
        if Context.root_block:
            self.blur(
                None,
                None,
                self,
                js="""
                () => {
                    return {
                        "__type__": "update",
                        "visible": false
                    }
                }
                """
            )

