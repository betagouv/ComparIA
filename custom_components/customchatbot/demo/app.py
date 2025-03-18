import gradio as gr
import json
from gradio_customchatbot import CustomChatbot


example = CustomChatbot().example_value()

# Create an example with the new JSON format that includes reasoning
example_with_reasoning = [
    {"role": "user", "content": "What is the capital of France?"},
    {
        "role": "assistant", 
        "content": json.dumps({
            "reasoning": "France is a country in Western Europe. Its capital city has been Paris since the Middle Ages. Paris is located on the Seine River and is known for landmarks like the Eiffel Tower.",
            "content": "The capital of France is Paris."
        }),
        "metadata": {"bot": "a"}
    },
    {"role": "user", "content": "What is the capital of Germany?"},
    {
        "role": "assistant", 
        "content": json.dumps({
            "reasoning": "Germany is a country in Central Europe. Berlin has been the capital of unified Germany since 1990 following the fall of the Berlin Wall and German reunification.",
            "content": "The capital of Germany is Berlin."
        }),
        "metadata": {"bot": "b"}
    }
]

with gr.Blocks() as demo:
    with gr.Row():
        CustomChatbot(
            value=example,
            show_copy_button=True,
            label="Standard Format",
            likeable=True,
            type="messages"
        )
    
    with gr.Row():
        CustomChatbot(
            value=example_with_reasoning,
            show_copy_button=True,
            label="With Reasoning (JSON Format)",
            likeable=True,
            type="messages"
        )


if __name__ == "__main__":
    demo.launch()
