UPDATE reactions
SET question_id = CONCAT(conversation_pair_id, '-', msg_rank)
WHERE question_id IS NULL;
