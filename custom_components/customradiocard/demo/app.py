
import gradio as gr
from gradio_customradiocard import CustomRadioCard


example = CustomRadioCard().example_value()

demo = gr.Interface(
    lambda x:x,
    CustomRadioCard(),  # interactive version of your component
    CustomRadioCard(),  # static version of your component
    # examples=[[example]],  # uncomment this line to view the "example version" of your component
)


if __name__ == "__main__":
    demo.launch()
