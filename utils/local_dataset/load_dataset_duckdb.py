"""
Prepare DuckDB database with ComparIA local exported datasets

This script creates a DuckDB database with the locally exported datasets.
Use start_duckdb.sh to launch the DuckDB CLI.
"""

from pathlib import Path

import duckdb

print("=" * 80)
print("PREPARING DUCKDB WITH COMPARIA LOCAL DATASETS")
print("=" * 80)

# Paths - parquets are in subdirectories from dry-run export
local_dataset_dir = Path(__file__).parent
db_path = local_dataset_dir / "comparia_local.duckdb"

# Create/connect to DuckDB database
print(f"\n📦 Creating database at: {db_path.absolute()}")
con = duckdb.connect(str(db_path))

# Install and load JSON extension for query compatibility
con.execute("INSTALL json")
con.execute("LOAD json")

# Load reactions
reactions_parquet = local_dataset_dir / "comparia-reactions" / "reactions.parquet"
if reactions_parquet.exists():
    print(f"\n📊 Loading reactions from: {reactions_parquet}")
    con.execute(f"""
        CREATE OR REPLACE TABLE reactions AS
        SELECT * FROM read_parquet('{reactions_parquet}')
    """)
    count = con.execute("SELECT COUNT(*) FROM reactions").fetchone()[0]
    print(f"   ✓ Loaded {count:,} reactions")
else:
    print(f"\n⚠️  Reactions not found at {reactions_parquet}")
    print("   Run: uv run python ../export_dataset.py --dry-run")

# Load conversations
conversations_parquet = (
    local_dataset_dir / "comparia-conversations" / "conversations.parquet"
)
if conversations_parquet.exists():
    print(f"\n📊 Loading conversations from: {conversations_parquet}")
    con.execute(f"""
        CREATE OR REPLACE TABLE conversations AS
        SELECT * FROM read_parquet('{conversations_parquet}')
    """)
    count = con.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    print(f"   ✓ Loaded {count:,} conversations")
else:
    print(f"\n⚠️  Conversations not found at {conversations_parquet}")
    print("   Run: uv run python ../export_dataset.py --dry-run")

# Load votes
votes_parquet = local_dataset_dir / "comparia-votes" / "votes.parquet"
if votes_parquet.exists():
    print(f"\n📊 Loading votes from: {votes_parquet}")
    con.execute(f"""
        CREATE OR REPLACE TABLE votes AS
        SELECT * FROM read_parquet('{votes_parquet}')
    """)
    count = con.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    print(f"   ✓ Loaded {count:,} votes")
else:
    print(f"\n⚠️  Votes not found at {votes_parquet}")

# Create some useful views
print(f"\n🔧 Creating useful views...")

# View: Reactions summary by model
con.execute("""
    CREATE OR REPLACE VIEW reactions_by_model AS
    SELECT
        refers_to_model,
        COUNT(*) as total_reactions,
        SUM(CASE WHEN liked THEN 1 ELSE 0 END) as likes,
        SUM(CASE WHEN disliked THEN 1 ELSE 0 END) as dislikes,
        SUM(CASE WHEN useful THEN 1 ELSE 0 END) as useful_count,
        SUM(CASE WHEN creative THEN 1 ELSE 0 END) as creative_count,
        SUM(CASE WHEN complete THEN 1 ELSE 0 END) as complete_count,
        SUM(CASE WHEN incorrect THEN 1 ELSE 0 END) as incorrect_count,
        SUM(CASE WHEN superficial THEN 1 ELSE 0 END) as superficial_count
    FROM reactions
    WHERE refers_to_model IS NOT NULL
    GROUP BY refers_to_model
    ORDER BY total_reactions DESC
""")
print("   ✓ Created view: reactions_by_model")

# View: Check for ModelResponseStream issues (should be 0 after filtering)
con.execute("""
    CREATE OR REPLACE VIEW check_modelresponsestream AS
    SELECT
        'response_content' as location,
        COUNT(*) as issue_count
    FROM reactions
    WHERE response_content LIKE '%ModelResponseStream%'
    UNION ALL
    SELECT
        'conversation_a_jsonb' as location,
        COUNT(*) as issue_count
    FROM reactions
    WHERE CAST(conversation_a AS VARCHAR) LIKE '%ModelResponseStream%'
    UNION ALL
    SELECT
        'conversation_b_jsonb' as location,
        COUNT(*) as issue_count
    FROM reactions
    WHERE CAST(conversation_b AS VARCHAR) LIKE '%ModelResponseStream%'
""")
print("   ✓ Created view: check_modelresponsestream")

# View: Reactions with comments
con.execute("""
    CREATE OR REPLACE VIEW reactions_with_comments AS
    SELECT
        id,
        timestamp,
        refers_to_model,
        liked,
        disliked,
        comment,
        question_content,
        LEFT(response_content, 200) as response_preview
    FROM reactions
    WHERE comment IS NOT NULL AND comment != ''
    ORDER BY timestamp DESC
""")
print("   ✓ Created view: reactions_with_comments")

# Show available tables and views
print("\n📋 Available tables and views:")
tables = con.execute("""
    SELECT table_name, table_type
    FROM information_schema.tables
    WHERE table_schema = 'main'
    ORDER BY table_type, table_name
""").fetchdf()
print(tables.to_string(index=False))

# Show basic statistics
print("\n📊 Dataset Statistics")
print("=" * 80)

if reactions_parquet.exists():
    reactions_count = con.execute("SELECT COUNT(*) FROM reactions").fetchone()[0]
    print(f"  Reactions: {reactions_count:,}")

if conversations_parquet.exists():
    conversations_count = con.execute("SELECT COUNT(*) FROM conversations").fetchone()[
        0
    ]
    print(f"  Conversations: {conversations_count:,}")

if votes_parquet.exists():
    votes_count = con.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    print(f"  Votes: {votes_count:,}")

print("\nℹ️  To verify data quality, run queries from: verify_dataset.sql")

# Close connection
con.close()

print("\n" + "=" * 80)
print("DATABASE READY")
print("=" * 80)
print(f"""
Database created: {db_path.absolute()}

Available tables:
  - reactions (filtered dataset)
  - conversations (filtered dataset)
  - votes (filtered dataset)

Useful views:
  - reactions_by_model (summary statistics by model)
  - reactions_with_comments (reactions that have user comments)
  - check_modelresponsestream (legacy check)

Data quality verification:
  - Copy/paste queries from verify_dataset.sql into DuckDB CLI
  - All queries are based on dataset/issue.md

To launch the DuckDB CLI, run:
  ./start_duckdb.sh

Or manually:
  duckdb comparia_local.duckdb
""")
