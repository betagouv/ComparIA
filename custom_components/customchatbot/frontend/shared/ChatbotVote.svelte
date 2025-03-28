<!-- 

with gr.Column(
# h-screen
visible=False,
elem_classes="fr-container min-h-screen fr-pt-4w",
elem_id="vote-area",
) as vote_area:
gr.HTML(
elem_classes="text-center",
value="""
<h4 class="fr-mt-2w fr-mb-1v">Quel modèle d’IA préférez-vous ?</h4>
<p class="text-grey fr-text--sm">Avant de découvrir l’identité des modèles, nous avons besoin de votre préférence.<br />Elle permet d'enrichir les jeux de données compar:IA dont l’objectif est d’affiner les futurs modèles d’IA sur le français</p>""",
)

which_model_radio = CustomRadioCard(
min_columns=1,
elem_id="vote-cards",
elem_classes="justify-center fr-mx-auto fr-col-12 fr-col-md-8",
choices=[
    (
        """<div class="self-center justify-center"><svg class="inline" width='26' height='26'><circle cx='13' cy='13' r='12' fill='#A96AFE' stroke='none'/></svg> <span class="">Modèle A</span>
    </div>""",
        "model-a",
    ),
    (
        """<span class="self-center text-center justify-center">Les deux se valent</span>""",
        "both-equal",
    ),
    (
        """<div class="self-center"><svg class="inline" width='26' height='26'><circle cx='13' cy='13' r='12' fill='#ff9575' stroke='none'/></svg><span class=""> Modèle B</span>
    </div>""",
        "model-b",
    ),
],
show_label=False,
)

with gr.Row(
visible=False,
elem_id="supervote-area",
elem_classes="fr-grid-row fr-grid-row--gutters gap-0 fr-mt-8w fr-mb-md-16w fr-mb-16w",
) as supervote_area:

with gr.Column(
    elem_classes="fr-col-12 fr-col-md-6 fr-mr-md-n1w fr-mb-1w bg-white rounded-tile"
):

    gr.HTML(
        value="""<p><svg class="inline" width='26' height='26'><circle cx='13' cy='13' r='12' fill='#A96AFE' stroke='none'/></svg> <strong>Modèle A</strong></p>
<p class="fr-mb-2w"><strong>Comment qualifiez-vous ses réponses ?</strong></p>"""
    )

    positive_a = gr.CheckboxGroup(
        elem_classes="thumb-up-icon flex-important checkboxes fr-mb-2w",
        show_label=False,
        choices=[
            ("Utiles", "useful"),
            ("Complètes", "complete"),
            ("Créatives", "creative"),
            ("Mise en forme claire", "clear-formatting"),
        ],
    )

    negative_a = gr.CheckboxGroup(
        elem_classes="thumb-down-icon flex-important checkboxes fr-mb-2w",
        show_label=False,
        choices=[
            ("Incorrectes", "incorrect"),
            ("Superficielles", "superficial"),
            ("Instructions non respectées", "instructions-not-followed"),
        ],
    )

    comments_a = FrInput(
        show_label=False,
        visible=False,
        lines=3,
        placeholder="Les réponses du modèle A sont...",
    )

with gr.Column(
    elem_classes="fr-col-12 fr-col-md-6 fr-ml-md-3w fr-mr-md-n3w fr-mb-1w bg-white rounded-tile"
):

    gr.HTML(
        value="""<p><svg class="inline" width='26' height='26'><circle cx='13' cy='13' r='12' fill='#ff9575' stroke='none'/></svg> <strong>Modèle B</strong></p>
<p class="fr-mb-2w"><strong>Comment qualifiez-vous ses réponses ?</strong></p>"""
    )

    positive_b = gr.CheckboxGroup(
        elem_classes="thumb-up-icon flex-important checkboxes fr-mb-2w",
        show_label=False,
        choices=[
            ("Utiles", "useful"),
            ("Complètes", "complete"),
            ("Créatives", "creative"),
            ("Mise en forme claire", "clear-formatting"),
        ],
    )

    negative_b = gr.CheckboxGroup(
        elem_classes="thumb-down-icon flex-important checkboxes fr-mb-2w",
        show_label=False,
        choices=[
            ("Incorrectes", "incorrect"),
            ("Superficielles", "superficial"),
            ("Instructions non respectées", "instructions-not-followed"),
        ],
    )
    comments_b = FrInput(
        show_label=False,
        visible=False,
        lines=3,
        placeholder="Les réponses du modèle B sont...",
    )
comments_link = gr.Button(
    elem_classes="link fr-mt-1w", value="Ajouter des détails"
) -->
