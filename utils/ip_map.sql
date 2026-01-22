-- FIXME rework visitor_id (remove ip-map hash) visitor_id: cookie or null
INSERT INTO ip_map (ip_address)
SELECT DISTINCT ip
FROM conversations
WHERE ip IS NOT NULL
ON CONFLICT (ip_address) DO NOTHING;

-- UPDATE conversations
-- SET ip_id = ip_map.id
-- FROM ip_map
-- WHERE conversations.ip = ip_map.ip_address;