import tiktoken
import json
import postgresql

def count_tokens(text, model="text-embedding-ada-002"):
    """Counts the number of tokens in a given text using tiktoken."""
    text = text.replace("\n", " ")
    return len(tiktoken.encoding_for_model(model).encode(text))

def process_conversation(conversation, role_prefix):
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

            metadata["output_tokens"] = output_tokens  # Add token count to metadata
            message["metadata"] = metadata
            enriched_conversation.append(message)

    return enriched_conversation, total_conv_output_tokens

def main(conv_a, conv_b, dsn, conversation_id):
    """Main function to connect to the database via DSN and process conversations."""
    try:
        conn = sql.connect(dsn)
        cursor = conn.cursor()

        enriched_conv_a, total_conv_a_output_tokens = process_conversation(conv_a, "conv_a")
        enriched_conv_b, total_conv_b_output_tokens = process_conversation(conv_b, "conv_b")

        try:
            cursor.execute(
                """
                UPDATE conversations
                SET
                    conv_a = ?,
                    conv_b = ?,
                    total_conv_a_output_tokens = ?,
                    total_conv_b_output_tokens = ?
                WHERE id = ?
                """,
                (json.dumps(enriched_conv_a), json.dumps(enriched_conv_b), total_conv_a_output_tokens, total_conv_b_output_tokens, conversation_id),
            )
            conn.commit()
            print(f"Conversation {conversation_id} updated.")
        except pyodbc.Error as e:
            print(f"Error updating conversation: {e}")
            conn.rollback()

        cursor.close()

    except pyodbc.Error as e:
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
        {"role": "assistant", "content": "Why don't scientists trust atoms? Because they make up everything!", "metadata": {}},
    ]

    # Replace with your DSN name and conversation ID
    dsn = "your_dsn_name"
    conversation_id = 1  # Replace with the ID of the conversation you want to update

    main(conv_a, conv_b, dsn, conversation_id)