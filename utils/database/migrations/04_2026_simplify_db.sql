-- Drop redondant columns (can be retrieved from related conversations)
ALTER TABLE votes DROP COLUMN visitor_id;
ALTER TABLE votes DROP COLUMN ip;
ALTER TABLE votes DROP COLUMN model_pair_name;
ALTER TABLE votes DROP COLUMN opening_msg;
ALTER TABLE votes DROP COLUMN model_a_name;
ALTER TABLE votes DROP COLUMN model_b_name;
ALTER TABLE votes DROP COLUMN system_prompt_a;
ALTER TABLE votes DROP COLUMN system_prompt_b;
ALTER TABLE votes DROP COLUMN conversation_a;
ALTER TABLE votes DROP COLUMN conversation_b;
