-- 13/10/2025
ALTER TABLE conversations DROP COLUMN model_a_total_params;
ALTER TABLE conversations DROP COLUMN model_b_total_params;
ALTER TABLE conversations DROP COLUMN model_a_active_params;
ALTER TABLE conversations DROP COLUMN model_b_active_params;
ALTER TABLE conversations DROP COLUMN total_conv_a_kwh;
ALTER TABLE conversations DROP COLUMN total_conv_b_kwh;
ALTER TABLE conversations DROP COLUMN country;
ALTER TABLE conversations DROP COLUMN city;

-- comma separated
ALTER TABLE conversations ADD COLUMN cohorts TEXT;
ALTER TABLE conversations ADD COLUMN country_portal VARCHAR(255);