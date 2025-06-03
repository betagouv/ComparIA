
import gradio as gr
from app import demo as app
import os

_docs = {'CustomDropdown': {'description': 'Creates a dropdown of choices from which a single entry or multiple entries can be selected (as an input component) or displayed (as an output component).\n', 'members': {'__init__': {'choices': {'type': 'Sequence[\n        str | int | float | tuple[str, str | int | float]\n    ]\n    | None', 'default': 'None', 'description': 'a list of string or numeric options to choose from. An option can also be a tuple of the form (name, value), where name is the displayed name of the dropdown choice and value is the value to be passed to the function, or returned by the function.'}, 'value': {'type': 'dict | Callable | DefaultValue | None', 'default': 'value = <gradio_customdropdown.customdropdown.DefaultValue object at 0x12a592850>', 'description': 'the value selected in dropdown. If `multiselect` is true, this should be list, otherwise a single string or number. By default, the first choice is initially selected. If set to None, no value is initially selected. If a callable, the function will be called whenever the app loads to set the initial value of the component.'}, 'type': {'type': 'Literal["value", "index"]', 'default': '"value"', 'description': 'type of value to be returned by component. "value" returns the string of the choice selected, "index" returns the index of the choice selected.'}, 'multiselect': {'type': 'bool | None', 'default': 'None', 'description': 'if True, multiple choices can be selected.'}, 'max_choices': {'type': 'int | None', 'default': 'None', 'description': 'maximum number of choices that can be selected. If None, no limit is enforced.'}, 'filterable': {'type': 'bool', 'default': 'True', 'description': 'if True, user will be able to type into the dropdown and filter the choices by typing. Can only be set to False if `allow_custom_value` is False.'}, 'label': {'type': 'str | None', 'default': 'None', 'description': 'the label for this component, displayed above the component if `show_label` is `True` and is also used as the header if there are a table of examples for this component. If None and used in a `gr.Interface`, the label will be the name of the parameter this component corresponds to.'}, 'info': {'type': 'str | None', 'default': 'None', 'description': 'additional component description, appears below the label in smaller font. Supports markdown / HTML syntax.'}, 'every': {'type': 'Timer | float | None', 'default': 'None', 'description': 'continuously calls `value` to recalculate it if `value` is a function (has no effect otherwise). Can provide a Timer whose tick resets `value`, or a float that provides the regular interval for the reset Timer.'}, 'inputs': {'type': 'Component | Sequence[Component] | set[Component] | None', 'default': 'None', 'description': 'components that are used as inputs to calculate `value` if `value` is a function (has no effect otherwise). `value` is recalculated any time the inputs change.'}, 'show_label': {'type': 'bool | None', 'default': 'None', 'description': 'if True, will display label.'}, 'container': {'type': 'bool', 'default': 'True', 'description': 'if True, will place the component in a container - providing some extra padding around the border.'}, 'scale': {'type': 'int | None', 'default': 'None', 'description': 'relative size compared to adjacent Components. For example if Components A and B are in a Row, and A has scale=2, and B has scale=1, A will be twice as wide as B. Should be an integer. scale applies in Rows, and to top-level Components in Blocks where fill_height=True.'}, 'min_width': {'type': 'int', 'default': '160', 'description': 'minimum pixel width, will wrap if not sufficient screen space to satisfy this value. If a certain scale value results in this Component being narrower than min_width, the min_width parameter will be respected first.'}, 'interactive': {'type': 'bool | None', 'default': 'None', 'description': 'if True, choices in this dropdown will be selectable; if False, selection will be disabled. If not provided, this is inferred based on whether the component is used as an input or output.'}, 'visible': {'type': 'bool', 'default': 'True', 'description': 'if False, component will be hidden.'}, 'elem_id': {'type': 'str | None', 'default': 'None', 'description': 'an optional string that is assigned as the id of this component in the HTML DOM. Can be used for targeting CSS styles.'}, 'elem_classes': {'type': 'list[str] | str | None', 'default': 'None', 'description': 'an optional list of strings that are assigned as the classes of this component in the HTML DOM. Can be used for targeting CSS styles.'}, 'render': {'type': 'bool', 'default': 'True', 'description': 'if False, component will not be rendered in the Blocks context. Should be used if the intention is to assign event listeners now but render the component later.'}, 'key': {'type': 'int | str | None', 'default': 'None', 'description': None}, 'models': {'type': 'list[dict] | None', 'description': None}}, 'postprocess': {'value': {'type': 'dict | None', 'description': "The output data received by the component from the user's function in the backend."}}, 'preprocess': {'return': {'type': 'dict | None', 'description': "The preprocessed input data sent to the user's function in the backend."}, 'value': None}}, 'events': {'change': {'type': None, 'default': None, 'description': 'Triggered when the value of the CustomDropdown changes either because of user input (e.g. a user types in a textbox) OR because of a function update (e.g. an image receives a value from the output of an event trigger). See `.input()` for a listener that is only triggered by user input.'}, 'input': {'type': None, 'default': None, 'description': 'This listener is triggered when the user changes the value of the CustomDropdown.'}, 'select': {'type': None, 'default': None, 'description': 'Event listener for when the user selects or deselects the CustomDropdown. Uses event data gradio.SelectData to carry `value` referring to the label of the CustomDropdown, and `selected` to refer to state of the CustomDropdown. See EventData documentation on how to use this event data'}, 'submit': {'type': None, 'default': None, 'description': 'This listener is triggered when the user presses the Enter key while the CustomDropdown is focused.'}, 'focus': {'type': None, 'default': None, 'description': 'This listener is triggered when the CustomDropdown is focused.'}, 'blur': {'type': None, 'default': None, 'description': 'This listener is triggered when the CustomDropdown is unfocused/blurred.'}, 'key_up': {'type': None, 'default': None, 'description': 'This listener is triggered when the user presses a key while the CustomDropdown is focused.'}}}, '__meta__': {'additional_interfaces': {}, 'user_fn_refs': {'CustomDropdown': []}}}

abs_path = os.path.join(os.path.dirname(__file__), "css.css")

with gr.Blocks(
    css=abs_path,
    theme=gr.themes.Default(
        font_mono=[
            gr.themes.GoogleFont("Inconsolata"),
            "monospace",
        ],
    ),
) as demo:
    gr.Markdown(
"""
# `gradio_customdropdown`

<div style="display: flex; gap: 7px;">
<img alt="Static Badge" src="https://img.shields.io/badge/version%20-%200.0.1%20-%20orange">  
</div>

Python library for easily interacting with trained machine learning models
""", elem_classes=["md-custom"], header_links=True)
    app.render()
    gr.Markdown(
"""
## Installation

```bash
pip install gradio_customdropdown
```

## Usage

```python
import gradio as gr
from gradio_customdropdown import CustomDropdown



demo = gr.Interface(
    lambda x: x,
    CustomDropdown(
        choices=["random", "big-models", "small-models", "custom"],
        models=[]
    ),
    CustomDropdown(
        choices=["random", "big-models", "small-models", "custom"],
        models=[]
    ),# interactive version of your component
    # examples=[
    #     [example]
    # ],  # uncomment this line to view the "example version" of your component
)


if __name__ == "__main__":
    demo.launch()

```
""", elem_classes=["md-custom"], header_links=True)


    gr.Markdown("""
## `CustomDropdown`

### Initialization
""", elem_classes=["md-custom"], header_links=True)

    gr.ParamViewer(value=_docs["CustomDropdown"]["members"]["__init__"], linkify=[])


    gr.Markdown("### Events")
    gr.ParamViewer(value=_docs["CustomDropdown"]["events"], linkify=['Event'])




    gr.Markdown("""

### User function

The impact on the users predict function varies depending on whether the component is used as an input or output for an event (or both).

- When used as an Input, the component only impacts the input signature of the user function.
- When used as an output, the component only impacts the return signature of the user function.

The code snippet below is accurate in cases where the component is used as both an input and an output.

- **As input:** Is passed, the preprocessed input data sent to the user's function in the backend.
- **As output:** Should return, the output data received by the component from the user's function in the backend.

 ```python
def predict(
    value: dict | None
) -> dict | None:
    return value
```
""", elem_classes=["md-custom", "CustomDropdown-user-fn"], header_links=True)




    demo.load(None, js=r"""function() {
    const refs = {};
    const user_fn_refs = {
          CustomDropdown: [], };
    requestAnimationFrame(() => {

        Object.entries(user_fn_refs).forEach(([key, refs]) => {
            if (refs.length > 0) {
                const el = document.querySelector(`.${key}-user-fn`);
                if (!el) return;
                refs.forEach(ref => {
                    el.innerHTML = el.innerHTML.replace(
                        new RegExp("\\b"+ref+"\\b", "g"),
                        `<a href="#h-${ref.toLowerCase()}">${ref}</a>`
                    );
                })
            }
        })

        Object.entries(refs).forEach(([key, refs]) => {
            if (refs.length > 0) {
                const el = document.querySelector(`.${key}`);
                if (!el) return;
                refs.forEach(ref => {
                    el.innerHTML = el.innerHTML.replace(
                        new RegExp("\\b"+ref+"\\b", "g"),
                        `<a href="#h-${ref.toLowerCase()}">${ref}</a>`
                    );
                })
            }
        })
    })
}

""")

demo.launch()
