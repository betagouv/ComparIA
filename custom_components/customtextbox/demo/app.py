
import gradio as gr
from gradio_customtextbox import CustomTextbox


example = CustomTextbox().example_value()

demo = gr.Interface(
    lambda x:x,
    CustomTextbox(),  # interactive version of your component
    CustomTextbox(),  # static version of your component
    # examples=[[example]],  # uncomment this line to view the "example version" of your component
)


if __name__ == "__main__":
    demo.launch()
