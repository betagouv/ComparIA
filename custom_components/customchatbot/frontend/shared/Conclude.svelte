<!-- 

with gr.Column(
elem_classes="fr-container--fluid fr-py-2w fr-grid-row",
elem_id="buttons-footer",
visible=False,
) as buttons_footer:

supervote_send_btn = gr.Button(
elem_classes="purple-btn fr-mx-auto fr-col-10 fr-col-md-4",
value="Passer à la révélation des modèles",
size="lg",
interactive=False,
)

with gr.Row(elem_classes="fr-grid-row fr-grid-row--center"):
    conclude_btn = gr.Button(
        size="lg",
        value="Passer à la révélation des modèles",
        elem_classes="fr-col-12 fr-col-md-5 purple-btn fr-mt-1w",
        visible=False,
        interactive=False,
    )
        
with gr.Column(
elem_id="reveal-screen", visible=False, elem_classes="min-h-screen fr-pt-4w"
) as reveal_screen:

results_area = gr.HTML(visible=True)

footer_area = gr.HTML(visible=True, value=footer_html) -->
