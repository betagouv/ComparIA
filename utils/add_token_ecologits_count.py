import tiktoken
import psycopg2
import json
import tomli
from psycopg2 import sql
from psycopg2.extras import Json, DictCursor

# Load model metadata from file (assuming TOML format)
with open("models-extra-info.toml", "rb") as f:
    MODELS = tomli.load(f)


def count_tokens(text):
    """Counts the number of tokens in a given text using tiktoken."""
    # text = text.replace("\n", " ")
    return len(tiktoken.get_encoding("cl100k_base").encode(text))


def process_conversation(conversation):
    """Processes a conversation, counts tokens, and returns enriched conversation and total tokens."""
    total_conv_output_tokens = 0
    enriched_conversation = []

    for message in conversation:
        content = message.get("content")
        metadata = message.get("metadata", {})
        output_tokens = 0

        if content:
            if metadata.get("output_tokens", 0) != 0:
                output_tokens = metadata.get("output_tokens", 0)
            else:
                output_tokens = count_tokens(content)

            if message.get("role") == "assistant":
                total_conv_output_tokens += output_tokens

            metadata["output_tokens"] = output_tokens
            message["metadata"] = metadata
            enriched_conversation.append(message)

    return enriched_conversation, total_conv_output_tokens


def get_model_metadata(model_name):
    """Get metadata for a specific model from the models file."""
    return MODELS.get(model_name, {})


def get_model_params(model_meta):
    """Extract params from model metadata, preferring params or summing total+active if available."""
    params = model_meta.get("params")
    if params is not None:
        return params
    total_params = model_meta.get("total_params")
    active_params = model_meta.get("active_params")
    if total_params is not None and active_params is not None:
        return total_params, active_params
    return None  # Return None if no params information found


def process_unprocessed_conversations(dsn, batch_size=10):
    """Process conversations in batches that don't have token counts."""
    conn = None
    try:
        conn = psycopg2.connect(dsn)

        while True:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                # Start a transaction
                conn.autocommit = False

                # Get batch of unprocessed conversations with model_a_name
                cursor.execute(
                    """
                    SELECT id, conversation_a, conversation_b, model_a_name, model_b_name
                    FROM conversations
                    WHERE total_conv_a_output_tokens IS NULL
                    OR total_conv_b_output_tokens IS NULL
                    ORDER BY id
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                    """,
                    (batch_size,),
                )

                conversations = cursor.fetchall()
                if not conversations:
                    break  # No more conversations to process

                for conv in conversations:
                    try:
                        # Get model metadata
                        model_meta = get_model_metadata(conv["model_a_name"])

                        # Process conversations
                        conv_a = (
                            json.loads(conv["conversation_a"])
                            if isinstance(conv["conversation_a"], str)
                            else conv["conversation_a"]
                        )
                        conv_b = (
                            json.loads(conv["conv_b"])
                            if isinstance(conv["conversation_b"], str)
                            else conv["conversation_b"]
                        )

                        enriched_conv_a, total_conv_a_tokens = process_conversation(
                            conv_a
                        )
                        enriched_conv_b, total_conv_b_tokens = process_conversation(
                            conv_b
                        )

                        model_a_meta = get_model_metadata(conv["model_a_name"])
                        model_b_meta = get_model_metadata(conv["model_b_name"])

                        # Get model parameters
                        model_a_params = get_model_params(model_a_meta)
                        model_b_params = get_model_params(model_b_meta)

                        # Update conversation with token counts and model metadata
                        cursor.execute(
                            """
                            UPDATE conversations
                            SET 
                                total_conv_a_output_tokens = %s,
                                total_conv_b_output_tokens = %s
                            WHERE id = %s
                            """,
                            (
                                total_conv_a_tokens,
                                total_conv_b_tokens,
                                conv["id"],
                            ),
                        )
                    # cursor.execute(
                    #                             """
                    #                             UPDATE conversations
                    #                             SET
                    #                                 conv_a = %s,
                    #                                 conv_b = %s,
                    #                                 total_conv_a_output_tokens = %s,
                    #                                 total_conv_b_output_tokens = %s,

                    # model_a_params = %s,
                    # model_b_params = %s
                    #                             WHERE id = %s
                    #                             """,
                    #                             (
                    #                                 Json(enriched_conv_a),
                    #                                 Json(enriched_conv_b),
                    # model_a_params,
                    # model_b_params,
                    #                                 total_conv_a_tokens,
                    #                                 total_conv_b_tokens,
                    #                                 conv["id"],
                    #                             ),
                    #                         )
                    except Exception as e:
                        print(f"Error processing conversation {conv['id']}: {e}")
                        conn.rollback()
                        continue

                conn.commit()
                print(f"Processed {len(conversations)} conversations")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    import os

    dsn = os.getenv("DATABASE_URI")

    if not dsn:
        raise ValueError("DATABASE_URI environment variable not set")

    process_unprocessed_conversations(dsn)
