"""gr.Dropdown() component."""

from __future__ import annotations

import warnings
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Literal

from gradio_client.documentation import document

from gradio.components.base import Component, FormComponent
from gradio.events import Events
from gradio.exceptions import Error

if TYPE_CHECKING:
    from gradio.components import Timer


class DefaultValue:
    # This sentinel is used to indicate that if the value is not explicitly set,
    # the first choice should be selected in the dropdown if multiselect is False,
    # and an empty list should be selected if multiselect is True.
    pass


DEFAULT_VALUE = DefaultValue()


class CustomDropdown(FormComponent):
    """
    Creates a dropdown of choices from which a single entry or multiple entries can be selected (as an input component) or displayed (as an output component).

    Demos: sentence_builder
    """

    EVENTS = [
        Events.change,
        Events.input,
        Events.select,
        Events.submit,
        Events.focus,
        Events.blur,
        Events.key_up,
    ]

    def __init__(
        self,
        choices: Sequence[str | int | float | tuple[str, str | int | float]]
        | None = None,
        *,
        value: str
        | int
        | float
        | Sequence[str | int | float]
        | Callable
        | DefaultValue
        | None = DEFAULT_VALUE,
        type: Literal["value", "index"] = "value",
        multiselect: bool | None = None,
        max_choices: int | None = None,
        filterable: bool = True,
        label: str | None = None,
        info: str | None = None,
        every: Timer | float | None = None,
        inputs: Component | Sequence[Component] | set[Component] | None = None,
        show_label: bool | None = None,
        container: bool = True,
        scale: int | None = None,
        min_width: int = 160,
        interactive: bool | None = None,
        visible: bool = True,
        elem_id: str | None = None,
        elem_classes: list[str] | str | None = None,
        render: bool = True,
        key: int | str | None = None,
        models: list[dict] | None,
    ):
        """
        Parameters:
            choices: a list of string or numeric options to choose from. An option can also be a tuple of the form (name, value), where name is the displayed name of the dropdown choice and value is the value to be passed to the function, or returned by the function.
            value: the value selected in dropdown. If `multiselect` is true, this should be list, otherwise a single string or number. By default, the first choice is initally selected. If set to None, no value is initally selected. If a callable, the function will be called whenever the app loads to set the initial value of the component.
            type: type of value to be returned by component. "value" returns the string of the choice selected, "index" returns the index of the choice selected.
            multiselect: if True, multiple choices can be selected.
            allow_custom_value: if True, allows user to enter a custom value that is not in the list of choices.
            max_choices: maximum number of choices that can be selected. If None, no limit is enforced.
            filterable: if True, user will be able to type into the dropdown and filter the choices by typing. Can only be set to False if `allow_custom_value` is False.
            label: the label for this component, displayed above the component if `show_label` is `True` and is also used as the header if there are a table of examples for this component. If None and used in a `gr.Interface`, the label will be the name of the parameter this component corresponds to.
            info: additional component description, appears below the label in smaller font. Supports markdown / HTML syntax.
            every: continously calls `value` to recalculate it if `value` is a function (has no effect otherwise). Can provide a Timer whose tick resets `value`, or a float that provides the regular interval for the reset Timer.
            inputs: components that are used as inputs to calculate `value` if `value` is a function (has no effect otherwise). `value` is recalculated any time the inputs change.
            show_label: if True, will display label.
            container: if True, will place the component in a container - providing some extra padding around the border.
            scale: relative size compared to adjacent Components. For example if Components A and B are in a Row, and A has scale=2, and B has scale=1, A will be twice as wide as B. Should be an integer. scale applies in Rows, and to top-level Components in Blocks where fill_height=True.
            min_width: minimum pixel width, will wrap if not sufficient screen space to satisfy this value. If a certain scale value results in this Component being narrower than min_width, the min_width parameter will be respected first.
            interactive: if True, choices in this dropdown will be selectable; if False, selection will be disabled. If not provided, this is inferred based on whether the component is used as an input or output.
            visible: if False, component will be hidden.
            elem_id: an optional string that is assigned as the id of this component in the HTML DOM. Can be used for targeting CSS styles.
            elem_classes: an optional list of strings that are assigned as the classes of this component in the HTML DOM. Can be used for targeting CSS styles.
            render: if False, component will not be rendered in the Blocks context. Should be used if the intention is to assign event listeners now but render the component later.
        """
        self.choices = (
            # Although we expect choices to be a list of tuples, it can be a list of lists if the Gradio app
            # is loaded with gr.load() since Python tuples are converted to lists in JSON.
            [tuple(c) if isinstance(c, (tuple, list)) else (str(c), c) for c in choices]
            if choices
            else []
        )
        valid_types = ["value", "index"]
        if type not in valid_types:
            raise ValueError(
                f"Invalid value for parameter `type`: {type}. Please choose from one of: {valid_types}"
            )
        self.type = type
        self.multiselect = multiselect

        if value == DEFAULT_VALUE:
            value = {"prompt_value": "random", "mode":"random", "custom_models_selection":[]}
        self.models = models
        self.max_choices = max_choices
        self.filterable = filterable
        super().__init__(
            label=label,
            info=info,
            every=every,
            inputs=inputs,
            show_label=show_label,
            container=container,
            scale=scale,
            min_width=min_width,
            interactive=interactive,
            visible=visible,
            elem_id=elem_id,
            elem_classes=elem_classes,
            render=render,
            key=key,
            value=value,
        )

    def api_info(self) -> dict[str, Any]:
        if self.multiselect:
            json_type = {
                "type": "array",
                "items": {"type": "string", "enum": [c[1] for c in self.choices]},
            }
        else:
            json_type = {
                "type": "string",
                "enum": [c[1] for c in self.choices],
            }
        return json_type

    def example_payload(self) -> Any:
        if self.multiselect:
            return [self.choices[0][1]] if self.choices else []
        else:
            return self.choices[0][1] if self.choices else None

    def example_value(self) -> Any:
        if self.multiselect:
            return [self.choices[0][1]] if self.choices else []
        else:
            return self.choices[0][1] if self.choices else None

    def preprocess(
        self, payload: dict | list[str | int | float | dict] | None
    ) -> dict | None:
        # if payload is None:
        #     return None

        print(f"preprocess payload: {str(payload)}")
        value = dict()
        try:
            value['prompt_value'] = payload['prompt_value']
            value['mode'] = payload['mode']
            value['custom_models_selection'] = payload['custom_models_selection']
            return value
            # return payload["prompt_value"]
        # if self.type == "value":
        #     return payload
        # elif self.type == "index":
        #     if isinstance(payload, list):
        #         return [
        #             choice_values.index(choice) if choice in choice_values else None
        #             for choice in payload
        #         ]
        #     else:
        #         return (
        #             choice_values.index(payload) if payload in choice_values else None
        #         )
        except:
            # raise ValueError(
            #     f"Unknown payload: {payload}."
            # )
            return payload

    def postprocess(
        self, value: dict | None
    ) -> str | int | float | list[str | int | float] | None:
        print(f"postprocess value: {str(value)}")
        if value is None:
            return None
        # FIXME: delete
        elif isinstance(value, str):
            # return value
            return {
            "prompt_value": value, 
            "mode": value, 
            }
        elif isinstance(value, dict):
        # else:
            return value
            # return {"prompt_value": value.prompt_value,
            # "mode": value.mode,
            # "custom_models_selection": value.custom_models_selection
            # }