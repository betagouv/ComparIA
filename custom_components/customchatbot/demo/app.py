import gradio as gr
from gradio_customchatbot import CustomChatbot


example = CustomChatbot().example_value()

with gr.Blocks() as demo:
    with gr.Row():
        CustomChatbot(
            value=example,
            show_copy_button=True,
            label="Populated",
            likeable=True,
        ),  # populated component


if __name__ == "__main__":
    demo.launch()
