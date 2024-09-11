

# def save_profile_to_db(data):
#     from languia.config import db as db_config

#     logger = logging.getLogger("languia")
#     if not db_config:
#         logger.warn("Cannot log to db: no db configured")
#         return
#     conn = psycopg2.connect(**db_config)
#     cursor = conn.cursor()
#     try:
#         insert_statement = sql.SQL(
#             """
#             INSERT INTO profiles (tstamp, chatbot_use, gender, age, profession, confirmed, session_hash, visitor_uuid, extra)
#             VALUES (%(tstamp)s, %(chatbot_use)s, %(gender)s, %(age)s, %(profession)s, %(confirmed)s, %(session_hash)s, %(visitor_uuid)s, %(extra)s)
#         """
#         )
#         values = {
#             "tstamp": (data["tstamp"]),
#             "chatbot_use": (data["chatbot_use"]),
#             "gender": (data["gender"]),
#             "age": (data["age"]),
#             "profession": (data["profession"]),
#             "confirmed": bool(data["confirmed"]),
#             "session_hash": str(data["session_hash"]),
#             "visitor_uuid": str(data["visitor_uuid"]),
#             "extra": json.dumps(data["extra"]),
#         }
#         cursor.execute(insert_statement, values)
#         conn.commit()
#         logger.info(f"Saved profile to db")
#     except Exception as e:
#         logger = logging.getLogger("languia")
#         logger.error(f"Error saving profile to db: {e}")
#         stacktrace = traceback.format_exc()
#         print(f"Stacktrace: {stacktrace}")
#     finally:
#         cursor.close()
#         if conn:
#             conn.close()


# def save_profile(
#     conversation_a,
#     conversation_b,
#     which_model_radio,
#     chatbot_use,
#     gender,
#     age,
#     profession,
#     confirmed,
#     request: gr.Request,
# ):
#     """
#     save poll data to file
#     """
#     logger = logging.getLogger("languia")
#     t = datetime.datetime.now()
#     profile_log_filename = f"profile-{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{request.session_hash}.json"
#     profile_log_path = os.path.join(LOGDIR, profile_log_filename)

#     visitor_uuid = get_matomo_tracker_from_cookies(request.cookies)

#     data = {
#         "tstamp": str(t),
#         "chatbot_use": chatbot_use,
#         "gender": gender,
#         "age": age,
#         "profession": profession,
#         "confirmed": bool(confirmed),
#         "session_hash": str(request.session_hash),
#         "visitor_uuid": str(visitor_uuid),
#         # Log redundant info to be sure
#         "extra": {
#             "which_model_radio": which_model_radio,
#             "models": [str(x.model_name) for x in [conversation_a, conversation_b]],
#             "messages": [
#                 messages_to_dict_list(x)
#                 for x in [conversation_a.messages, conversation_b.messages]
#             ],
#             # "cookies": dict(request.cookies),
#         },
#     }
#     # logger.info(f"poll", extra={"request": request,
#     #          "chatbot_use":chatbot_use, "gender":gender, "age":age, "profession":profession
#     #     },
#     # )
#     with open(profile_log_path, "a") as fout:
#         fout.write(json.dumps(data) + "\n")

#     save_profile_to_db(data=data)
#     logger.info("profile_filled", extra={"request": request, "extra_data": data})

#     return data


# with Modal(elem_id="quiz-modal") as quiz_modal:
#     gr.Markdown(
#         """
#                 ### Dernière étape
#                 Ces quelques informations sur votre profil permettront à la recherche d’affiner les réponses des futurs modèles.
#                 """
#     )
#     profession = gr.Dropdown(
#         choices=[
#             ("Agriculteur", "farmer"),
#             (
#                 "Artisan, commerçant et chef d'entreprise",
#                 "artisan_merchant_and_business_owner",
#             ),
#             (
#                 "Cadre et profession intellectuelle supérieure",
#                 "executive_and_senior_intellectual_profession",
#             ),
#             ("Profession intermédiaire", "intermediate_profession"),
#             ("Étudiant", "student"),
#             ("Employé", "employee"),
#             ("Ouvrier", "worker"),
#             ("Retraité", "retired"),
#             ("Sans emploi", "unemployed"),
#             ("Ne se prononce pas", "no_opinion"),
#         ],
#         label="Catégorie socioprofessionnelle",
#     )

#     age = gr.Dropdown(
#         choices=[
#             ("Moins de 18 ans", "under_18"),
#             ("Entre 18 et 24 ans", "18_to_24"),
#             ("Entre 25 et 34 ans", "25_to_34"),
#             ("Entre 35 et 44 ans", "35_to_44"),
#             ("Entre 45 et 54 ans", "45_to_54"),
#             ("Entre 55 et 64 ans", "55_to_64"),
#             ("Plus de 64 ans", "over_64"),
#             ("Ne se prononce pas", "no_opinion"),
#         ],
#         label="Tranche d'âge",
#     )

#     gender = gr.Dropdown(
#         choices=[
#             ("Femme", "female"),
#             ("Homme", "male"),
#             ("Autre", "other"),
#             ("Ne se prononce pas", "no_opinion"),
#         ],
#         label="Genre",
#     )
#     chatbot_use = gr.Dropdown(
#         choices=[
#             ("Tous les jours", "every_day"),
#             ("Toutes les semaines", "every_week"),
#             ("Une fois par mois", "once_a_month"),
#             ("Moins d'une fois par mois", "less_than_once_a_month"),
#             ("Jamais", "never"),
#             ("Ne se prononce pas", "no_opinion"),
#         ],
#         label="Fréquence d'utilisation d'assistants conversationnels",
#     )
#     with gr.Row(elem_classes="fr-grid-row fr-grid-row--gutters fr-grid-row--right"):
#         skip_poll_btn = gr.Button("Passer", elem_classes="fr-btn fr-btn--secondary")
#         send_poll_btn = gr.Button("Envoyer", elem_classes="fr-btn")


# @send_poll_btn.click(
#     inputs=[
#         conversations[0],
#         conversations[1],
#         which_model_radio_output,
#         chatbot_use,
#         gender,
#         age,
#         profession,
#     ],
#     outputs=[
#         quiz_modal,
#         stepper_block,
#         vote_area,
#         supervote_area,
#         feedback_row,
#         results_area,
#         buttons_footer,
#     ],
#     api_name=False,
# )
# @skip_poll_btn.click(
#     inputs=[
#         conversations[0],
#         conversations[1],
#         which_model_radio_output,
#         chatbot_use,
#         gender,
#         age,
#         profession,
#     ],
#     outputs=[
#         quiz_modal,
#         stepper_block,
#         vote_area,
#         supervote_area,
#         feedback_row,
#         results_area,
#         buttons_footer,
#     ],
#     api_name=False,
# )
# def send_poll(
#     conversation_a,
#     conversation_b,
#     which_model_radio_output,
#     chatbot_use,
#     gender,
#     age,
#     profession,
#     request: gr.Request,
#     event: gr.EventData,
# ):
#     confirmed = event.target.value == "Envoyer"  # Not "Passer"

#     save_profile(
#         conversation_a,
#         conversation_b,
#         which_model_radio_output,
#         chatbot_use,
#         gender,
#         age,
#         profession,
#         confirmed,
#         request,
#     )