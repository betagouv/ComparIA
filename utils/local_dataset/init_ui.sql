-- Initialize DuckDB UI
-- This file is loaded when starting duckdb with -init flag

-- Enable the HTTP server for the UI
INSTALL httpserver;
LOAD httpserver;

-- Start the UI on port 3000
SELECT duckdb_web_server_start();

-- Show welcome message
SELECT '🦆 DuckDB UI started at http://localhost:3000' as message;
SELECT 'Available tables: reactions, conversations, votes' as info;
SELECT 'Try: SELECT * FROM check_modelresponsestream;' as tip;
