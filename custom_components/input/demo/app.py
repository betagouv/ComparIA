
import gradio as gr
from gradio_nostyleinput import NoStyleInput


example = NoStyleInput().example_value()

demo = gr.Interface(
    lambda x:x,
    NoStyleInput(),  # interactive version of your component
    NoStyleInput(),  # static version of your component
    # examples=[[example]],  # uncomment this line to view the "example version" of your component
)


if __name__ == "__main__":
    demo.launch()
