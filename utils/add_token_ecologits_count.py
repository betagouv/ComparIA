import tiktoken
import psycopg2
import json
from psycopg2 import sql
from psycopg2.extras import Json

def count_tokens(text):
    """Counts the number of tokens in a given text using tiktoken."""
    text = text.replace("\n", " ")
    return len(tiktoken.get_encoding("cl100k_base").encode(text))


def process_conversation(
    conversation, role_prefix=None
):  # role_prefix parameter kept for compatibility
    """Processes a conversation, counts tokens, and returns enriched conversation and total tokens."""
    total_conv_output_tokens = 0
    enriched_conversation = []

    for message in conversation:
        content = message.get("content")
        metadata = message.get("metadata", {})
        output_tokens = 0

        if content:
            output_tokens = count_tokens(content)

            if message.get("role") == "assistant":
                total_conv_output_tokens += output_tokens

            metadata["output_tokens"] = output_tokens
            message["metadata"] = metadata
            enriched_conversation.append(message)

    return enriched_conversation, total_conv_output_tokens


def main(conv_a, conv_b, dsn, conversation_id):
    """Main function to connect to PostgreSQL and process conversations."""
    conn = None
    try:
        conn = psycopg2.connect(dsn)
        cursor = conn.cursor()

        enriched_conv_a, total_conv_a_output_tokens = process_conversation(conv_a)
        enriched_conv_b, total_conv_b_output_tokens = process_conversation(conv_b)

        try:
            cursor.execute(
                sql.SQL(
                    """
                    UPDATE conversations
                    SET
                        total_conv_a_output_tokens = %s,
                        total_conv_b_output_tokens = %s
                    WHERE id = %s
                """
                ),
                (
                    total_conv_a_output_tokens,
                    total_conv_b_output_tokens,
                    conversation_id,
                ),
                # sql.SQL(
                #     """
                #     UPDATE conversations
                #     SET
                #         conv_a = %s,
                #         conv_b = %s,
                #         total_conv_a_output_tokens = %s,
                #         total_conv_b_output_tokens = %s
                #     WHERE id = %s
                # """
                # ),
            )
            conn.commit()
            print(f"Conversation {conversation_id} updated.")
        except psycopg2.Error as e:
            print(f"Error updating conversation: {e}")
            conn.rollback()

        cursor.close()

    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
    finally:
        if conn:
            conn.close()


# Example usage:
if __name__ == "__main__":
    conv_a = [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!", "metadata": {}},
    ]
    conv_b = [
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "Tell me a joke."},
        {
            "role": "assistant",
            "content": "Why don't scientists trust atoms? Because they make up everything!",
            "metadata": {},
        },
    ]

    # Replace with your PostgreSQL connection string
    import os
    dsn = os.getenv("DATABASE_URI")
    conversation_id = 1

    main(conv_a, conv_b, dsn, conversation_id)
