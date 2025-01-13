SELECT
    conversation_pair_id,
    CASE
        WHEN model_pos = 'a' AND liked = TRUE THEN 'a'
        WHEN model_pos = 'b' AND disliked = TRUE THEN 'a'
        WHEN model_pos = 'a' AND disliked = TRUE THEN 'b'
        WHEN model_pos = 'b' AND liked = TRUE THEN 'b'
        ELSE 'none'
    END AS preferred_model
FROM reactions
GROUP BY conversation_pair_id, model_pos, liked, disliked;
