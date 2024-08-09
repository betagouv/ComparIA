
import gradio as gr
from app import demo as app
import os

_docs = {'CustomSlider': {'description': 'Creates a slider that ranges from {minimum} to {maximum} with a step size of {step}.\n', 'members': {'__init__': {'minimum': {'type': 'float', 'default': '0', 'description': 'minimum value for slider.'}, 'maximum': {'type': 'float', 'default': '100', 'description': 'maximum value for slider.'}, 'range_labels': {'type': 'list[str] | None', 'default': 'None', 'description': 'text labels for slider values.'}, 'extrema': {'type': 'list[str] | None', 'default': 'None', 'description': 'will display one text at each side of the component.'}, 'value': {'type': 'float | Callable | None', 'default': 'None', 'description': 'default value. If callable, the function will be called whenever the app loads to set the initial value of the component. Ignored if randomized=True.'}, 'step': {'type': 'float | None', 'default': 'None', 'description': 'increment between slider values.'}, 'label': {'type': 'str | None', 'default': 'None', 'description': 'The label for this component. Appears above the component and is also used as the header if there are a table of examples for this component. If None and used in a `gr.Interface`, the label will be the name of the parameter this component is assigned to.'}, 'info': {'type': 'str | None', 'default': 'None', 'description': 'additional component description.'}, 'every': {'type': 'Timer | float | None', 'default': 'None', 'description': 'Continously calls `value` to recalculate it if `value` is a function (has no effect otherwise). Can provide a Timer whose tick resets `value`, or a float that provides the regular interval for the reset Timer.'}, 'inputs': {'type': 'Component | list[Component] | set[Component] | None', 'default': 'None', 'description': 'Components that are used as inputs to calculate `value` if `value` is a function (has no effect otherwise). `value` is recalculated any time the inputs change.'}, 'show_label': {'type': 'bool | None', 'default': 'None', 'description': 'if True, will display label.'}, 'container': {'type': 'bool', 'default': 'True', 'description': 'If True, will place the component in a container - providing some extra padding around the border.'}, 'scale': {'type': 'int | None', 'default': 'None', 'description': 'relative size compared to adjacent Components. For example if Components A and B are in a Row, and A has scale=2, and B has scale=1, A will be twice as wide as B. Should be an integer. scale applies in Rows, and to top-level Components in Blocks where fill_height=True.'}, 'min_width': {'type': 'int', 'default': '160', 'description': 'minimum pixel width, will wrap if not sufficient screen space to satisfy this value. If a certain scale value results in this Component being narrower than min_width, the min_width parameter will be respected first.'}, 'interactive': {'type': 'bool | None', 'default': 'None', 'description': 'if True, slider will be adjustable; if False, adjusting will be disabled. If not provided, this is inferred based on whether the component is used as an input or output.'}, 'visible': {'type': 'bool', 'default': 'True', 'description': 'If False, component will be hidden.'}, 'elem_id': {'type': 'str | None', 'default': 'None', 'description': 'An optional string that is assigned as the id of this component in the HTML DOM. Can be used for targeting CSS styles.'}, 'elem_classes': {'type': 'list[str] | str | None', 'default': 'None', 'description': 'An optional list of strings that are assigned as the classes of this component in the HTML DOM. Can be used for targeting CSS styles.'}, 'render': {'type': 'bool', 'default': 'True', 'description': 'If False, component will not render be rendered in the Blocks context. Should be used if the intention is to assign event listeners now but render the component later.'}, 'key': {'type': 'int | str | None', 'default': 'None', 'description': 'if assigned, will be used to assume identity across a re-render. Components that have the same key across a re-render will have their value preserved.'}, 'randomize': {'type': 'bool', 'default': 'False', 'description': 'If True, the value of the slider when the app loads is taken uniformly at random from the range given by the minimum and maximum.'}}, 'postprocess': {'value': {'type': 'float | None', 'description': 'Expects an {int} or {float} returned from function and sets slider value to it as long as it is within range (otherwise, sets to minimum value).'}}, 'preprocess': {'return': {'type': 'float', 'description': 'Passes slider value as a {float} into the function.'}, 'value': None}}, 'events': {'change': {'type': None, 'default': None, 'description': 'Triggered when the value of the CustomSlider changes either because of user input (e.g. a user types in a textbox) OR because of a function update (e.g. an image receives a value from the output of an event trigger). See `.input()` for a listener that is only triggered by user input.'}, 'input': {'type': None, 'default': None, 'description': 'This listener is triggered when the user changes the value of the CustomSlider.'}, 'release': {'type': None, 'default': None, 'description': 'This listener is triggered when the user releases the mouse on this CustomSlider.'}}}, '__meta__': {'additional_interfaces': {}, 'user_fn_refs': {'CustomSlider': []}}}

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
# `gradio_customslider`

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
pip install gradio_customslider
```

## Usage

```python

import gradio as gr
from gradio_customslider import CustomSlider


example = CustomSlider().example_value()

demo = gr.Interface(
    lambda x:x,
    CustomSlider(),  # interactive version of your component
    CustomSlider(),  # static version of your component
    # examples=[[example]],  # uncomment this line to view the "example version" of your component
)


if __name__ == "__main__":
    demo.launch()

```
""", elem_classes=["md-custom"], header_links=True)


    gr.Markdown("""
## `CustomSlider`

### Initialization
""", elem_classes=["md-custom"], header_links=True)

    gr.ParamViewer(value=_docs["CustomSlider"]["members"]["__init__"], linkify=[])


    gr.Markdown("### Events")
    gr.ParamViewer(value=_docs["CustomSlider"]["events"], linkify=['Event'])




    gr.Markdown("""

### User function

The impact on the users predict function varies depending on whether the component is used as an input or output for an event (or both).

- When used as an Input, the component only impacts the input signature of the user function.
- When used as an output, the component only impacts the return signature of the user function.

The code snippet below is accurate in cases where the component is used as both an input and an output.

- **As input:** Is passed, passes slider value as a {float} into the function.
- **As output:** Should return, expects an {int} or {float} returned from function and sets slider value to it as long as it is within range (otherwise, sets to minimum value).

 ```python
def predict(
    value: float
) -> float | None:
    return value
```
""", elem_classes=["md-custom", "CustomSlider-user-fn"], header_links=True)




    demo.load(None, js=r"""function() {
    const refs = {};
    const user_fn_refs = {
          CustomSlider: [], };
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
