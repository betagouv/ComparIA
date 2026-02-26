-- ============================================================================
-- ComparIA Dataset Quality Verification
-- ============================================================================
-- Copy/paste these queries in DuckDB CLI to verify data quality
-- After export with filtering, reactions issues should all be 0
-- ============================================================================

-- Basic statistics: reactions
SELECT
    'Total reactions' as metric,
    COUNT(*) as value
FROM reactions;

-- Basic statistics: conversations
SELECT
    'Total conversations' as metric,
    COUNT(*) as value
FROM conversations;

-- Basic statistics: votes
SELECT
    'Total votes' as metric,
    COUNT(*) as value
FROM votes;


-- Issue 1: msg_index out of bounds (expected 0 after filtering, was 1.1% = 904)
SELECT
    'msg_index_out_of_bounds' as issue_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM reactions), 2) as percentage
FROM reactions
WHERE msg_index >= LEAST(
    json_array_length(CAST(conversation_a AS JSON)),
    json_array_length(CAST(conversation_b AS JSON))
);

-- Issue 2: Message at msg_index not assistant role (expected 0 after filtering, was 1.6% = 1,348)
SELECT
    'msg_not_assistant' as issue_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM reactions), 2) as percentage
FROM reactions
WHERE CASE
    WHEN refers_to_conv_id = conv_a_id THEN
        json_extract(CAST(conversation_a AS JSON), '$[' || msg_index || '].role') != '"assistant"'
    WHEN refers_to_conv_id = conv_b_id THEN
        json_extract(CAST(conversation_b AS JSON), '$[' || msg_index || '].role') != '"assistant"'
    ELSE true
END;

-- Issue 3: ModelResponseStream in response_content (expected 0 after filtering, was 14.0% = 11,912)
SELECT
    'modelresponsestream_in_response_content' as issue_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM reactions), 2) as percentage
FROM reactions
WHERE response_content LIKE '%ModelResponseStream%';

-- Issue 4: ModelResponseStream in JSONB conversations (expected 0 after filtering, was ~43 reactions)
SELECT
    'modelresponsestream_in_jsonb' as issue_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM reactions), 2) as percentage
FROM reactions
WHERE CAST(conversation_a AS VARCHAR) LIKE '%ModelResponseStream%'
OR CAST(conversation_b AS VARCHAR) LIKE '%ModelResponseStream%';

-- ============================================================================
-- CONVERSATIONS DATASET - Quality Issues
-- ============================================================================
-- Expected percentages:
--   - not_ending_with_assistant: 19.57% (5,870 / 30,000)
--   - mismatched_pair_sizes: 1.78% (535 / 30,000)
--   - modelresponsestream_messages: 0.45% (136 / 30,000)
-- Note: After filtering, modelresponsestream should be 0
-- ============================================================================

-- Issue 1: Conversations not ending with assistant message (expected ~19.57%)
SELECT
    'not_ending_with_assistant' as issue_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM conversations), 2) as percentage
FROM conversations
WHERE json_extract(
    CAST(conversation_a AS JSON),
    '$[' || (json_array_length(CAST(conversation_a AS JSON)) - 1) || '].role'
) != '"assistant"'
OR json_extract(
    CAST(conversation_b AS JSON),
    '$[' || (json_array_length(CAST(conversation_b AS JSON)) - 1) || '].role'
) != '"assistant"';

-- Issue 2: Mismatched conversation pair sizes (expected some %)
SELECT
    'mismatched_pair_sizes' as issue_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM conversations), 2) as percentage
FROM conversations
WHERE json_array_length(CAST(conversation_a AS JSON)) !=
      json_array_length(CAST(conversation_b AS JSON));

-- Issue 3: ModelResponseStream in conversations (expected 0 after filtering)
SELECT
    'modelresponsestream_in_conversations' as issue_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM conversations), 2) as percentage
FROM conversations
WHERE CAST(conversation_a AS VARCHAR) LIKE '%ModelResponseStream%'
OR CAST(conversation_b AS VARCHAR) LIKE '%ModelResponseStream%';


-- ============================================================================
-- ADDITIONAL CHECKS
-- ============================================================================

-- Check most common msg_index values (from issue.md: 75.5% at index 1)
SELECT
    msg_index,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM reactions), 2) as percentage
FROM reactions
GROUP BY msg_index
ORDER BY count DESC
LIMIT 10;


-- ============================================================================
-- SPAM DETECTION - Quality Verification
-- ============================================================================
-- After spam filtering, these counts should be 0
-- Checks for patterns defined in backend/arena/spam_patterns.json
-- ============================================================================

-- Issue: Spam patterns in conversations (expected 0 after filtering)
SELECT
    'spam_patterns_in_conversations' as issue_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM conversations), 2) as percentage
FROM conversations
WHERE CAST(conversation_a AS VARCHAR) LIKE '%<Conversation>%'
   OR CAST(conversation_b AS VARCHAR) LIKE '%<Conversation>%'
   OR CAST(conversation_a AS VARCHAR) LIKE '%Begin your response to the most recent message%'
   OR CAST(conversation_b AS VARCHAR) LIKE '%Begin your response to the most recent message%'
   OR CAST(conversation_a AS VARCHAR) LIKE '%<User>%'
   OR CAST(conversation_b AS VARCHAR) LIKE '%<User>%';

-- Issue: Spam patterns in reactions (expected 0 after filtering)
SELECT
    'spam_patterns_in_reactions' as issue_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM reactions), 2) as percentage
FROM reactions
WHERE CAST(conversation_a AS VARCHAR) LIKE '%<Conversation>%'
   OR CAST(conversation_b AS VARCHAR) LIKE '%<Conversation>%'
   OR CAST(conversation_a AS VARCHAR) LIKE '%Begin your response to the most recent message%'
   OR CAST(conversation_b AS VARCHAR) LIKE '%Begin your response to the most recent message%'
   OR CAST(conversation_a AS VARCHAR) LIKE '%<User>%'
   OR CAST(conversation_b AS VARCHAR) LIKE '%<User>%';

