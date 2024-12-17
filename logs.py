import logging
import psycopg2
import json

def save_log(data):
    from languia.config import db as db_config

    logger = logging.getLogger("languia")
    if not db_config:
        logger.warn("Cannot log to db: no db configured")
        return
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    try:
        insert_statement = psycopg2.sql.SQL(
            """
            INSERT INTO logs (tstamp, session_hash, data)
            VALUES (%(tstamp)s, %(session_hash)s, %(data)s)

        """
        )
        values = json.dumps(data)
        cursor.execute(insert_statement, values)
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving vote to db: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Common:
# timestamp
# app_version (commit)
# error level?
# session_hash

# def init_arene(session_hash: str, ip: str, cookie: str):
#     return


# def picked_models(self, model_a: str, model_b: str):
#     return


# def response_a(
#     self,
#     duration: float,
#     length: int,
#     content: str,
#     endpoint_api: str,
#     model_name: str,
#     impact: str,
# ):
#     return


# def response_b(
#     self,
#     duration: float,
#     length: int,
#     content: str,
#     endpoint_api: str,
#     model_name: str,
#     impact: str,
# ):
#     return


# def repicked_model(
#     api_error: str,
#     api_error_msg: str,
#     old_model_name: str,
#     model_name: str,
# ):
#     return

# def msg_user(
    # question:str,
    # is_unedited_prompt: bool):

# def clicked_category(
    # category: str,
    # result: str):

# def clicked_shuffle(
    # category: str,
    # result: str):

# def reacted():
#     reaction_id: str,

# def voted(
#     vote_id: str,):

# def reinit_arena( bool):

# def go_to_li?t( bool):

def session_issue(reason: str, session_hash: str):
    save_log(data={reason: reason, session_hash: session_hash})