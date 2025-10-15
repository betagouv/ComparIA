import gradio as gr
from languia.block_arena import demo
from languia import config

# Ensure static paths are set correctly
gr.set_static_paths(paths=[config.assets_absolute_path])

# Launch the Gradio app directly
if __name__ == "__main__":
    demo.launch(
        root_path="/arene",
        server_name="0.0.0.0",
        server_port=7860,  # Default Gradio port
        share=False,  # Set to True if you want to create a shareable link
    )
