import gradio as gr
import json
from gradio_customchatbot import CustomChatbot


example = CustomChatbot().example_value()

with gr.Blocks() as demo:
    with gr.Row():
        CustomChatbot(
            value=example,
            show_copy_button=True,
            label="Standard Format",
            likeable=True,
            type="messages"
        )
    

if __name__ == "__main__":
    demo.launch()
