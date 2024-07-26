import os
import json
import psycopg2
from psycopg2 import sql

# Database connection parameters
DB_HOST = 'localhost'
DB_NAME = 'your_database'
DB_USER = 'your_username'
DB_PASS = 'your_password'

# Directory containing the JSON files
json_directory = '/path/to/json/files/'

# Connect to PostgreSQL
try:
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    cur = conn.cursor()
    print("Successfully connected to the database")


# CREATE TABLE conversation_logs (
#     id SERIAL PRIMARY KEY,
#     tstamp DOUBLE PRECISION,
#     type TEXT,
#     model TEXT,
#     gen_params JSONB,
#     start DOUBLE PRECISION,
#     finish DOUBLE PRECISION,
#     state JSONB,
#     ip TEXT,
#     details JSONB
# );
#     {"tstamp": 1721641381.569, "type": "chat", "model": "Mixtral-8x7B-Instruct-v0.1", "gen_params": {"temperature": 0.7, "top_p": 1.0, "max_new_tokens": 1024}, "start": 1721641377.5814, "finish": 1721641381.569, "state": {"template_name": "mistral", "system_message": "", "roles": ["[INST]", "[/INST]"], "messages": [["[INST]", "Transforme cette phrase en un style soutenu et formel, tel que tu pourrais le lire dans un document officiel : \u201cJe suis malade et ne pourrai pas travailler aujourd\u2019hui. La r\u00e9union est report\u00e9e \u00e0 la semaine prochaine."], ["[/INST]", "Veuillez prendre note que, en raison de mon \u00e9tat de sant\u00e9 actuel, je suis dans l'incapacit\u00e9 de remplir mes obligations professionnelles pour aujourd'hui. Par cons\u00e9quent, il m'est malheureusement n\u00e9cessaire de reporter la r\u00e9union pr\u00e9vue \u00e0 la semaine prochaine. Je vous remercie de votre compr\u00e9hension et vous tiendrai inform\u00e9 de tout d\u00e9veloppement pertinent."]], "offset": 0, "conv_id": "52da471689ca4dbb8ee829650c8fe96e", "model_name": "Mixtral-8x7B-Instruct-v0.1"}, "ip": "127.0.0.1"}
# {"tstamp": 1721641394.5033, "type": "bothbad", "models": ["Mixtral-8x7B-Instruct-v0.1", "phi-3-mini-4k-instruct"], "conversations_state": [{"template_name": "mistral", "system_message": "", "roles": ["[INST]", "[/INST]"], "messages": [["[INST]", "Transforme cette phrase en un style soutenu et formel, tel que tu pourrais le lire dans un document officiel : \u201cJe suis malade et ne pourrai pas travailler aujourd\u2019hui. La r\u00e9union est report\u00e9e \u00e0 la semaine prochaine."], ["[/INST]", "Veuillez prendre note que, en raison de mon \u00e9tat de sant\u00e9 actuel, je suis dans l'incapacit\u00e9 de remplir mes obligations professionnelles pour aujourd'hui. Par cons\u00e9quent, il m'est malheureusement n\u00e9cessaire de reporter la r\u00e9union pr\u00e9vue \u00e0 la semaine prochaine. Je vous remercie de votre compr\u00e9hension et vous tiendrai inform\u00e9 de tout d\u00e9veloppement pertinent."]], "offset": 0, "conv_id": "52da471689ca4dbb8ee829650c8fe96e", "model_name": "Mixtral-8x7B-Instruct-v0.1"}, {"template_name": "zero_shot", "system_message": "A chat between a curious human and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the human's questions.", "roles": ["Human", "Assistant"], "messages": [["Human", "Transforme cette phrase en un style soutenu et formel, tel que tu pourrais le lire dans un document officiel : \u201cJe suis malade et ne pourrai pas travailler aujourd\u2019hui. La r\u00e9union est report\u00e9e \u00e0 la semaine prochaine."], ["Assistant", "Veuillez accepter mes sinc\u00e8res excuses pour mon absence inattendue aujourd'hui, due \u00e0 des affaires de sant\u00e9. Il est \u00e0 regretter que je ne puisse participer au rendez-vous professionnel programm\u00e9 pour cette journ\u00e9e. Suite \u00e0 cela, la rencontre a \u00e9t\u00e9 avantageusement repouss\u00e9e \u00e0 la semaine suivante afin de garantir la pr\u00e9sence de tous les participants."]], "offset": 0, "conv_id": "1d5db435400d4bc09a64d094d1fa0ecc", "model_name": "phi-3-mini-4k-instruct"}], "ip": "127.0.0.1", "details": {"chosen_model": "bothbad", "ressenti": [], "pertinence": [], "comprehension": [], "originalite": [], "comments": ""}}
# {"tstamp": 1721641786.6565, "type": "chat", "model": "phi-3-mini-4k-instruct", "gen_params": {"temperature": 0.7, "top_p": 1.0, "max_new_tokens": 1024}, "start": 1721641783.7006, "finish": 1721641786.6565, "state": {"template_name": "zero_shot", "system_message": "A chat between a curious human and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the human's questions.", "roles": ["Human", "Assistant"], "messages": [["Human", "Quoque ch'est qu'te berdoules ? R\u00e9ponds en Chtimi."], ["Assistant", "Je suis un assistant en IA, donc je n'ai pas de langage propre ni de langage familier tel que \"chtimi\". Ma programmation est en fran\u00e7ais, et je peux r\u00e9pondre \u00e0 des questions ou aider dans de nombreux domaines en utilisant le fran\u00e7ais standard. Je suis l\u00e0 pour vous assister avec vos questions dans cette langue."]], "offset": 0, "conv_id": "cf3989ccb4d547cbab893b63c7f13274", "model_name": "phi-3-mini-4k-instruct"}, "ip": "127.0.0.1"}

    # Loop through each JSON file in the directory
    for filename in os.listdir(json_directory):
        if filename.endswith('.json'):
            file_path = os.path.join(json_directory, filename)

            with open(file_path, 'r') as file:
                data = json.load(file)

                # Prepare SQL INSERT statement
                insert_query = sql.SQL("""
                INSERT INTO conversation_logs (tstamp, type, model, gen_params, start, finish, state, ip, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """)

                # Extract values from JSON
                tstamp = data.get('tstamp')
                type_ = data.get('type')
                model = data.get('model', None)
                gen_params = json.dumps(data.get('gen_params', {}))
                start = data.get('start', None)
                finish = data.get('finish', None)
                state = json.dumps(data.get('state', {}))
                ip = data.get('ip', None)
                details = json.dumps(data.get('details', {}))

                # Execute the insert statement
                cur.execute(insert_query, (
                    tstamp,
                    type_,
                    model,
                    gen_params,
                    start,
                    finish,
                    state,
                    ip,
                    details
                ))

    # Commit changes and close the connection
    conn.commit()
    print("Data successfully inserted into the database")

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if cur:
        cur.close()
    if conn:
        conn.close()
    print("Database connection closed")