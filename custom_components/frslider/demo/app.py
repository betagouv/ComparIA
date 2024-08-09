
import gradio as gr
from gradio_frslider import FrSlider


example = FrSlider().example_value()

demo = gr.Interface(
    lambda x:x,
    FrSlider(),  # interactive version of your component
    FrSlider(),  # static version of your component
    # examples=[[example]],  # uncomment this line to view the "example version" of your component
)


if __name__ == "__main__":
    demo.launch()
