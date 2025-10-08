import tiktoken
import psycopg2
import json
from psycopg2.extras import DictCursor


def count_tokens(text):
    """Counts the number of tokens in a given text using tiktoken."""
    num_tokens = len(tiktoken.get_encoding("cl100k_base").encode(text))
    if num_tokens == 0 and text:
        print(f"DEBUG: count_tokens returned 0 for non-empty text: '{text[:100]}...'")
    elif num_tokens == 0 and not text:
        print("DEBUG: count_tokens returned 0 for empty text.")
    return num_tokens


def process_conversation(conversation):
    """Processes a conversation, counts tokens for assistant messages, and returns enriched conversation and total assistant tokens."""
    print("Processing conversation...")
    if not conversation:
        print("DEBUG: process_conversation received an empty conversation.")
        return [], 0

    total_assistant_output_tokens = 0
    enriched_conversation = []

    # Filter only assistant messages for metadata checks
    assistant_messages = [msg for msg in conversation if msg.get("role") == "assistant"]

    metadata_filled = any(
        "output_tokens" in msg.get("metadata", {}) for msg in assistant_messages
    )
    metadata_not_filled = any(
        "output_tokens" not in msg.get("metadata", {}) for msg in assistant_messages
    )

    if metadata_filled and metadata_not_filled:
        input(
            "WARNING: Some assistant messages have 'output_tokens' in metadata, while others don't."
        )

    for message in conversation:
        content = message.get("content")
        metadata = message.get("metadata", {})
        output_tokens = 0
        role = message.get("role")
        existing_output_tokens = metadata.get("output_tokens")

        if content:
            if role == "assistant":
                if existing_output_tokens is not None and existing_output_tokens != 0:
                    output_tokens = existing_output_tokens
                    computed_tokens = count_tokens(content)
                    if computed_tokens != output_tokens:
                        input(
                            f"WARNING: Computed output tokens ({computed_tokens}) differ from existing metadata output tokens ({output_tokens}) for assistant message."
                        )
                else:
                    output_tokens = count_tokens(content)

                total_assistant_output_tokens += output_tokens

                metadata["output_tokens"] = output_tokens
                message["metadata"] = metadata
            enriched_conversation.append(message)

    print(
        f"Conversation processed. Total assistant output tokens: {total_assistant_output_tokens}"
    )
    if total_assistant_output_tokens == 0 and assistant_messages:
        print(
            "WARNING: process_conversation returned 0 total assistant tokens for an assistant-answered conversation."
        )
    elif total_assistant_output_tokens == 0 and not assistant_messages:
        print(
            "DEBUG: process_conversation returned 0 total assistant tokens for an unanswered."
        )
    return enriched_conversation, total_assistant_output_tokens


def process_unprocessed_conversations(dsn, batch_size=10):
    """Process conversations in batches that don't have token counts."""
    print("Starting process_unprocessed_conversations...")
    conn = None
    processed_count = 0
    error_count = 0
    try:
        print(f"Connecting to the database using DSN: '{dsn}'")
        conn = psycopg2.connect(dsn)
        print("Successfully connected to the database.")

        while True:
            print("Starting a new batch processing loop...")
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                # Start a transaction
                conn.autocommit = False
                print("Transaction started.")

                # Get batch of unprocessed conversations with model_a_name
                query = """
                    SELECT id, conversation_a, conversation_b, model_a_name, model_b_name
                    FROM conversations
                    WHERE (total_conv_a_output_tokens IS NULL OR total_conv_b_output_tokens IS NULL)
                    AND postprocess_failed IS FALSE
                    ORDER BY id
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                    """
                print(
                    f"Executing query to fetch {batch_size} unprocessed conversations: '{cursor.mogrify(query, (batch_size,)).decode()}'"
                )
                cursor.execute(
                    query,
                    (batch_size,),
                )

                conversations = cursor.fetchall()
                if not conversations:
                    print("No more unprocessed conversations found. Exiting loop.")
                    break  # No more conversations to process

                num_conversations_in_batch = len(conversations)
                print(
                    f"Fetched {num_conversations_in_batch} conversations for processing in this batch."
                )
                batch_processed_count = 0
                batch_error_count = 0

                for conv in conversations:
                    conversation_id = conv["id"]
                    print(f"Processing conversation with ID: {conversation_id}")
                    try:

                        # Process conversations
                        conv_a_raw = conv["conversation_a"]
                        conv_b_raw = conv["conversation_b"]
                        print(f"  Processing conversation A (ID: {conversation_id})...")
                        conv_a = (
                            json.loads(conv_a_raw)
                            if isinstance(conv_a_raw, str)
                            else conv_a_raw
                        )
                        enriched_conv_a, total_conv_a_tokens = process_conversation(
                            conv_a
                        )
                        print(
                            f"  Conversation A (ID: {conversation_id}) processed. Total output tokens: {total_conv_a_tokens}"
                        )

                        print(f"  Processing conversation B (ID: {conversation_id})...")
                        conv_b = (
                            json.loads(conv_b_raw)
                            if isinstance(conv_b_raw, str)
                            else conv_b_raw
                        )
                        enriched_conv_b, total_conv_b_tokens = process_conversation(
                            conv_b
                        )
                        print(
                            f"  Conversation B (ID: {conversation_id}) processed. Total output tokens: {total_conv_b_tokens}"
                        )

                        # Update conversation with token counts and model metadata
                        update_query = """
                            UPDATE conversations
                            SET
                                total_conv_a_output_tokens = %s,
                                total_conv_b_output_tokens = %s,
                                conv_a = %s,
                                conv_b = %s
                            WHERE id = %s
                            """
                        # model_a_total_params = %s,
                        # model_a_active_params = %s,
                        # model_b_total_params = %s,
                        # model_b_active_params = %s,
                        # total_conv_a_kwh = %s,
                        # total_conv_b_kwh = %s
                        print(
                            f"  Executing update query for conversation ID {conversation_id}: '{cursor.mogrify(update_query, (total_conv_a_tokens, total_conv_b_tokens, model_a_params, model_a_active_params, model_b_params, model_b_active_params, total_conv_a_kwh, total_conv_b_kwh, conversation_id)).decode()}'"
                        )
                        cursor.execute(
                            update_query,
                            (
                                total_conv_a_tokens,
                                total_conv_b_tokens,
                                enriched_conv_a,
                                enriched_conv_b,
                                conversation_id,
                            ),
                        )
                        batch_processed_count += 1
                        #                                 conv_a = %s,
                        #                                 conv_b = %s,

                        #                                 Json(enriched_conv_a),
                    except Exception as e:
                        print(f"Error processing conversation {conversation_id}: {e}")
                        batch_error_count += 1
                        # Mark the conversation as failed
                        mark_failed_query = """
                            UPDATE conversations
                            SET postprocess_failed = TRUE
                            WHERE id = %s
                        """
                        print(
                            f"  Marking conversation ID {conversation_id} as failed: '{cursor.mogrify(mark_failed_query, (conversation_id,)).decode()}'"
                        )
                        cursor.execute(mark_failed_query, (conversation_id,))
                        continue

                print(
                    f"Committing transaction for the processed batch of {num_conversations_in_batch} conversations."
                )
                conn.commit()
                print(
                    f"Processed {batch_processed_count} conversations successfully in this batch."
                )
                print(f"Encountered {batch_error_count} errors in this batch.")
                processed_count += batch_processed_count
                error_count += batch_error_count

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
            print("Transaction rolled back due to database error.")
    finally:
        if conn:
            print("Closing the database connection.")
            conn.close()
            print("Database connection closed.")

    print("Finished process_unprocessed_conversations.")
    print(f"\n--- Batch Processing Summary ---")
    print(f"Total conversations processed: {processed_count}")
    print(f"Total errors encountered: {error_count}")


if __name__ == "__main__":
    import os

    dsn = os.getenv("DATABASE_URI")

    if not dsn:
        error_message = "DATABASE_URI environment variable not set"
        print(f"Error: {error_message}")
        raise ValueError(error_message)

    print(f"Starting the main execution. DATABASE_URI is set.")
    process_unprocessed_conversations(dsn)
    print("Finished the main execution.")
