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
