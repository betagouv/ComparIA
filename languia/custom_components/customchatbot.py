"""gr.Chatbot() component."""

from __future__ import annotations

import inspect
import warnings
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Optional,
    TypedDict,
    Union,
    cast,
)

from gradio_client import utils as client_utils
from gradio_client.documentation import document
from pydantic import Field
from typing_extensions import NotRequired

from gradio import utils
from gradio.component_meta import ComponentMeta
from gradio.components import (
    Component as GradioComponent,
)
from gradio.components.base import Component
from gradio.data_classes import FileData, GradioModel, GradioRootModel
from gradio.events import Events
from gradio.exceptions import Error


class MetadataDict(TypedDict):
    bot: Union[str, None]
    duration: Union[float, None]
    generation_id: Union[str, None]


class FileDataDict(TypedDict):
    path: str  # server filepath
    url: NotRequired[Optional[str]]  # normalised server url
    size: NotRequired[Optional[int]]  # size in bytes
    orig_name: NotRequired[Optional[str]]  # original filename
    mime_type: NotRequired[Optional[str]]
    is_stream: NotRequired[bool]
    meta: dict[Literal["_type"], Literal["gradio.FileData"]]


class MessageDict(TypedDict):
    content: str | FileDataDict | tuple | Component
    role: Literal["user", "assistant", "system"]
    metadata: NotRequired[MetadataDict]
    error: NotRequired[Optional[str]]

    reasoning: NotRequired[str]


class FileMessage(GradioModel):
    file: FileData
    alt_text: Optional[str] = None


class Metadata(GradioModel):
    bot: Optional[Literal["a", "b"]] = None
    duration: Optional[float] = None
    generation_id: Optional[str] = None
    output_tokens: Optional[int] = None


class Message(GradioModel):
    role: str
    error: Optional[str] = None
    metadata: Metadata = Field(default_factory=Metadata)

    content: str
    reasoning: Optional[str] = None


class ExampleMessage(TypedDict):
    icon: NotRequired[
        str | FileDataDict
    ]  # filepath or url to an image to be shown in example box
    display_text: NotRequired[
        str
    ]  # text to be shown in example box. If not provided, main_text will be shown
    text: NotRequired[str]  # text to be added to chatbot when example is clicked
    files: NotRequired[
        Sequence[str | FileDataDict]
    ]  # list of file paths or URLs to be added to chatbot when example is clicked


@dataclass
class ChatMessage:
    role: Literal["user", "assistant", "system"]
    content: str | FileData | Component | FileDataDict | tuple | list
    error: Optional[str] = None
    reasoning: str | None = None
    metadata: MetadataDict | Metadata = field(default_factory=Metadata)


class ChatbotDataMessages(GradioRootModel):
    root: list[Message]


if TYPE_CHECKING:
    from gradio.components import Timer


def import_component_and_data(
    component_name: str,
) -> GradioComponent | ComponentMeta | Any | None:
    try:
        for component in utils.get_all_components():
            if component_name == component.__name__ and isinstance(
                component, ComponentMeta
            ):
                return component
    except ModuleNotFoundError as e:
        raise ValueError(f"Error importing {component_name}: {e}") from e
    except AttributeError:
        pass


class CustomChatbot(Component):
    """
    Creates a chatbot that displays user-submitted messages and responses. Supports a subset of Markdown including bold, italics, code, tables.
    Also supports audio/video/image files, which are displayed in the CustomChatbot, and other kinds of files which are displayed as links. This
    component is usually used as an output component.

    Demos: chatbot_simple, chatbot_streaming, chatbot_with_tools, chatbot_core_components
    Guides: creating-a-chatbot-fast, creating-a-custom-chatbot-with-blocks, agents-and-tool-usage
    """

    EVENTS = [
        Events.change,
        Events.select,
        Events.like,
        Events.retry,
        # Events.error,
        # "error",
        # Events.undo,
        # Events.example_select,
        Events.clear,
    ]

    def __init__(
        self,
        value: list[MessageDict | Message] | Callable | None = None,
        label: str | None = None,
        every: Timer | float | None = None,
        inputs: Component | Sequence[Component] | set[Component] | None = None,
        show_label: bool | None = None,
        container: bool = True,
        scale: int | None = None,
        min_width: int = 160,
        visible: bool = True,
        elem_id: str | None = None,
        elem_classes: list[str] | str | None = None,
        autoscroll: bool = True,
        render: bool = True,
        key: int | str | None = None,
        height: int | str | None = 400,
        max_height: int | str | None = None,
        min_height: int | str | None = None,
        latex_delimiters: list[dict[str, str | bool]] | None = None,
        rtl: bool = False,
        likeable: bool = False,
        show_copy_button: bool = False,
        avatar_images: tuple[str | Path | None, str | Path | None] | None = None,
        interactive: bool = True,
        sanitize_html: bool = True,
        render_markdown: bool = True,
        bubble_full_width: bool = True,
        line_breaks: bool = True,
        layout: Literal["panel", "bubble"] | None = None,
        placeholder: str | None = None,
        examples: list[ExampleMessage] | None = None,
        show_copy_all_button=False,
    ):
        """
        Parameters:
            value: Default list of messages to show in chatbot, where each message is of the format {"role": "user", "content": "Help me."}. Role can be one of "user", "assistant", or "system". Content should be either text, or media passed as a Gradio component, e.g. {"content": gr.Image("lion.jpg")}. If callable, the function will be called whenever the app loads to set the initial value of the component.
            type: The format of the messages passed into the chat history parameter of `fn`. If "messages", passes the value as a list of dictionaries with openai-style "role" and "content" keys. The "content" key's value should be one of the following - (1) strings in valid Markdown (2) a dictionary with a "path" key and value corresponding to the file to display or (3) an instance of a Gradio component. At the moment Image, Plot, Video, Gallery, Audio, and HTML are supported. The "role" key should be one of 'user' or 'assistant'. Any other roles will not be displayed in the output. If this parameter is 'tuples', expects a `list[list[str | None | tuple]]`, i.e. a list of lists. The inner list should have 2 elements: the user message and the response message, but this format is deprecated.
            label: the label for this component. Appears above the component and is also used as the header if there are a table of examples for this component. If None and used in a `gr.Interface`, the label will be the name of the parameter this component is assigned to.
            every: Continously calls `value` to recalculate it if `value` is a function (has no effect otherwise). Can provide a Timer whose tick resets `value`, or a float that provides the regular interval for the reset Timer.
            inputs: Components that are used as inputs to calculate `value` if `value` is a function (has no effect otherwise). `value` is recalculated any time the inputs change.
            show_label: if True, will display label.
            container: If True, will place the component in a container - providing some extra padding around the border.
            scale: relative size compared to adjacent Components. For example if Components A and B are in a Row, and A has scale=2, and B has scale=1, A will be twice as wide as B. Should be an integer. scale applies in Rows, and to top-level Components in Blocks where fill_height=True.
            min_width: minimum pixel width, will wrap if not sufficient screen space to satisfy this value. If a certain scale value results in this Component being narrower than min_width, the min_width parameter will be respected first.
            visible: If False, component will be hidden.
            elem_id: An optional string that is assigned as the id of this component in the HTML DOM. Can be used for targeting CSS styles.
            elem_classes: An optional list of strings that are assigned as the classes of this component in the HTML DOM. Can be used for targeting CSS styles.
            autoscroll: If True, will automatically scroll to the bottom of the textbox when the value changes, unless the user scrolls up. If False, will not scroll to the bottom of the textbox when the value changes.
            render: If False, component will not render be rendered in the Blocks context. Should be used if the intention is to assign event listeners now but render the component later.
            key: if assigned, will be used to assume identity across a re-render. Components that have the same key across a re-render will have their value preserved.
            height: The height of the component, specified in pixels if a number is passed, or in CSS units if a string is passed. If messages exceed the height, the component will scroll.
            max_height: The maximum height of the component, specified in pixels if a number is passed, or in CSS units if a string is passed. If messages exceed the height, the component will scroll. If messages are shorter than the height, the component will shrink to fit the content. Will not have any effect if `height` is set and is smaller than `max_height`.
            min_height: The minimum height of the component, specified in pixels if a number is passed, or in CSS units if a string is passed. If messages exceed the height, the component will expand to fit the content. Will not have any effect if `height` is set and is larger than `min_height`.
            latex_delimiters: A list of dicts of the form {"left": open delimiter (str), "right": close delimiter (str), "display": whether to display in newline (bool)} that will be used to render LaTeX expressions. If not provided, `latex_delimiters` is set to `[{ "left": "$$", "right": "$$", "display": True }]`, so only expressions enclosed in $$ delimiters will be rendered as LaTeX, and in a new line. Pass in an empty list to disable LaTeX rendering. For more information, see the [KaTeX documentation](https://katex.org/docs/autorender.html).
            rtl: If True, sets the direction of the rendered text to right-to-left. Default is False, which renders text left-to-right.
            show_copy_button: If True, will show a copy button for each chatbot message.
            avatar_images: Tuple of two avatar image paths or URLs for user and bot (in that order). Pass None for either the user or bot image to skip. Must be within the working directory of the Gradio app or an external URL.
            sanitize_html: If False, will disable HTML sanitization for chatbot messages. This is not recommended, as it can lead to security vulnerabilities.
            render_markdown: If False, will disable Markdown rendering for chatbot messages.
            bubble_full_width: If False, the chat bubble will fit to the content of the message. If True (default), the chat bubble will be the full width of the component.
            line_breaks: If True (default), will enable Github-flavored Markdown line breaks in chatbot messages. If False, single new lines will be ignored. Only applies if `render_markdown` is True.
            layout: If "panel", will display the chatbot in a llm style layout. If "bubble", will display the chatbot with message bubbles, with the user and bot messages on alterating sides. Will default to "bubble".
            placeholder: a placeholder message to display in the chatbot when it is empty. Centered vertically and horizontally in the CustomChatbot. Supports Markdown and HTML. If None, no placeholder is displayed.
            examples: A list of example messages to display in the chatbot before any user/assistant messages are shown. Each example should be a dictionary with an optional "text" key representing the message that should be populated in the CustomChatbot when clicked, an optional "files" key, whose value should be a list of files to populate in the CustomChatbot, an optional "icon" key, whose value should be a filepath or URL to an image to display in the example box, and an optional "display_text" key, whose value should be the text to display in the example box. If "display_text" is not provided, the value of "text" will be displayed.
            show_copy_all_button: If True, will show a copy all button that copies all chatbot messages to the clipboard.
        """
        self.data_model = ChatbotDataMessages
        self.autoscroll = autoscroll
        self.height = height
        self.max_height = max_height
        self.min_height = min_height
        self.rtl = rtl
        if latex_delimiters is None:
            latex_delimiters = [{"left": "$$", "right": "$$", "display": True}]
        self.latex_delimiters = latex_delimiters
        self.render_markdown = render_markdown
        self.show_copy_button = show_copy_button
        self.sanitize_html = sanitize_html
        self.bubble_full_width = bubble_full_width
        self.line_breaks = line_breaks
        self.likeable = likeable
        self.layout = layout
        self.show_copy_all_button = show_copy_all_button
        self.interactive = interactive
        super().__init__(
            interactive=interactive,
            label=label,
            every=every,
            inputs=inputs,
            show_label=show_label,
            container=container,
            scale=scale,
            min_width=min_width,
            visible=visible,
            elem_id=elem_id,
            elem_classes=elem_classes,
            render=render,
            key=key,
            value=value,
        )
        self.avatar_images: list[dict | None] = [None, None]
        if avatar_images is None:
            pass
        else:
            self.avatar_images = [
                self.serve_static_file(avatar_images[0]),
                self.serve_static_file(avatar_images[1]),
            ]
        self.placeholder = placeholder

        self.examples = examples

    @staticmethod
    def _check_format(messages: list[Any]):
        all_valid = all(
            isinstance(message, dict)
            and "role" in message
            and "content" in message
            or isinstance(message, ChatMessage | Message)
            for message in messages
        )
        if not all_valid:
            raise Error(
                "Data incompatible with messages format. Each message should be a dictionary with 'role' and 'content' keys or a ChatMessage object."
            )

    def _preprocess_content(
        self,
        chat_message: str | None,
    ) -> str | None:
        if chat_message is None:
            return None
        return chat_message

    def preprocess(
        self,
        payload: ChatbotDataMessages | None,
    ) -> list[MessageDict] | None:
        """
        Parameters:
            payload: data as a ChatbotData object
        Returns:
            Passes the value as a list of dictionaries with 'role' and 'content' keys. The `content` key's value is a string.
        """
        if payload is None:
            return payload
        if not isinstance(payload, ChatbotDataMessages):
            raise Error("Data incompatible with the messages format")
        message_dicts = []
        for message in payload.root:
            message_dict = cast(MessageDict, message.model_dump())
            message_dict["content"] = self._preprocess_content(message.content)
            if hasattr(message, "reasoning") and message.reasoning != "":
                message_dict["reasoning"] = message.reasoning
            message_dicts.append(message_dict)
        return message_dicts

    @staticmethod
    def _get_alt_text(chat_message: dict | list | tuple | GradioComponent):
        if isinstance(chat_message, dict):
            return chat_message.get("alt_text")
        elif not isinstance(chat_message, GradioComponent) and len(chat_message) > 1:
            return chat_message[1]

    @staticmethod
    def _create_file_message(chat_message, filepath):
        mime_type = client_utils.get_mimetype(filepath)

        return FileMessage(
            file=FileData(path=filepath, mime_type=mime_type),
            alt_text=CustomChatbot._get_alt_text(chat_message),
        )

    def _postprocess_content(
        self,
        chat_message: str | None,
    ) -> str | None:
        if chat_message is None:
            return None
        return chat_message

    def _postprocess_message_messages(
        self, message: MessageDict | ChatMessage
    ) -> Message:
        if isinstance(message, dict):
            message["content"] = self._postprocess_content(message["content"])
            msg = Message(**message)  # type: ignore
        elif isinstance(message, ChatMessage):
            message.content = self._postprocess_content(message.content)  # type: ignore
            msg = Message(
                role=message.role,
                content=message.content,  # type: ignore
                metadata=message.metadata,  # type: ignore
                error=message.error,  # type: ignore
                reasoning=message.reasoning,  # type: ignore
            )
        elif isinstance(message, Message):
            return message
        else:
            raise Error(
                f"Invalid message for CustomChatbot component: {message}", visible=False
            )

        msg.content = (
            inspect.cleandoc(msg.content)
            if isinstance(msg.content, str)
            else msg.content
        )
        return msg

    def postprocess(
        self,
        value: list[MessageDict | Message] | None,
    ) -> ChatbotDataMessages:
        """
        Parameters:
            value: Passes the value as a list of dictionaries with 'role' and 'content' keys. The `content` key's value is a string.
        Returns:
            an object of type ChatbotDataMessages
        """
        if value is None:
            return ChatbotDataMessages(root=[])
        self._check_format(value)
        processed_messages = [
            self._postprocess_message_messages(cast(MessageDict, message))
            for message in value
        ]
        return ChatbotDataMessages(root=processed_messages)

    def example_payload(self) -> Any:
        return [
            Message(role="user", content="Hello!").model_dump(),
            Message(role="assistant", content="How can I help you?").model_dump(),
        ]

    def example_value(self) -> Any:
        return [
            Message(role="user", content="Hello!").model_dump(),
            Message(
                role="assistant",
                content="How can I help you?",
                reasoning="This is a sample response",
            ).model_dump(),
        ]
