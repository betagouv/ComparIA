import os
import hashlib
import logging
import pandas as pd
from sqlalchemy import create_engine, text, exc

# Configure logging (adjust as needed)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Handles loading identifier mappings (IP to ID, Session Hash to IP ID)
    from a database and transforming dataframes by hashing visitor IDs
    and applying fallbacks based on session hashes.
    """

    def __init__(self, database_uri: str):
        """
        Initializes the DataProcessor with the database connection URI.

        Args:
            database_uri: The SQLAlchemy database connection string.
        """
        if not database_uri:
            logger.error("Database URI is required for initialization.")
            raise ValueError("DATABASE_URI cannot be empty.")

        self.database_uri = database_uri
        self.engine = None
        self.ip_to_id_map = {}         # Stores mapping: {ip_address: unique_id}
        self.session_hash_to_ip_id_map = {} # Stores mapping: {session_hash: unique_ip_id}
        self._initialize_engine()

    def _initialize_engine(self):
        """Initializes the SQLAlchemy engine."""
        try:
            # Create a single engine for reuse.
            # Consider connection pooling options for high-concurrency scenarios.
            self.engine = create_engine(self.database_uri)
            logger.info("Database engine created successfully.")
        except Exception as e:
            logger.exception(f"Failed to create database engine: {e}")
            self.engine = None # Ensure engine is None if creation fails
            raise ConnectionError(f"Could not create database engine: {e}") from e

    def _ensure_engine(self):
        """Checks if the engine is initialized, raises error if not."""
        if not self.engine:
             logger.error("Database engine is not initialized. Cannot proceed.")
             raise ConnectionError("Database engine is not available. Initialize the DataProcessor correctly.")

    @staticmethod
    def _hash_md5(value: str | None) -> str | None:
        """
        Computes the MD5 hash of a given string.

        Args:
            value: The string to hash.

        Returns:
            The hexadecimal MD5 hash string, or None if the input is None or empty.
        """
        if not value:
            return None
        try:
            return hashlib.md5(value.encode("utf-8")).hexdigest()
        except Exception as e:
            logger.error(f"Error hashing value: {e}")
            return None # Or re-raise depending on desired behavior

    def load_mappings(self) -> bool:
        """
        Loads both the IP-to-ID and Session-Hash-to-IP-ID mappings from the database.

        Returns:
            True if both mappings were loaded successfully, False otherwise.
        """
        logger.info("Starting to load identifier mappings...")
        ip_loaded = self._load_ip_to_id_mapping()
        session_loaded = self._load_session_hash_to_ip_id_mapping()

        if ip_loaded and session_loaded:
            logger.info("All identifier mappings loaded successfully.")
            return True
        else:
            logger.error("Failed to load one or more identifier mappings.")
            # Optionally clear partially loaded maps
            # self.ip_to_id_map = {}
            # self.session_hash_to_ip_id_map = {}
            return False

    def _load_ip_to_id_mapping(self) -> bool:
        """
        Loads the IP address to unique ID mapping from the database.
        It first ensures all distinct IPs from 'conversations' are in 'ip_map',
        then loads the mapping into memory.
        """
        self._ensure_engine()
        logger.info("Loading IP-to-ID mapping...")

        try:
            with self.engine.connect() as conn:
                # --- Transaction Block ---
                with conn.begin(): # Start transaction
                    logger.info("Ensuring all distinct IPs from 'conversations' exist in 'ip_map' table...")
                    # Insert distinct IPs from conversations into ip_map if they don't exist
                    insert_sql = text("""
                        INSERT INTO ip_map (ip_address)
                        SELECT DISTINCT ip
                        FROM conversations
                        WHERE ip IS NOT NULL
                        ON CONFLICT (ip_address) DO NOTHING;
                    """)
                    result = conn.execute(insert_sql)
                    logger.info(f"Inserted {result.rowcount} new IP addresses into 'ip_map'.")
                    # No explicit commit needed here, 'conn.begin()' handles it on success

                # --- Separate Read Operation ---
                logger.info("Fetching complete IP-to-ID mapping from 'ip_map' table...")
                # Use stream_results for potentially large tables, though it loads into pandas memory eventually
                query_engine = create_engine(self.database_uri, execution_options={"stream_results": True})
                with query_engine.connect() as read_conn:
                     # Load the entire mapping table
                     ip_map_df = pd.read_sql_query("SELECT id, ip_address FROM ip_map WHERE ip_address IS NOT NULL", read_conn)

                if ip_map_df.empty:
                    logger.warning("Loaded IP-to-ID mapping is empty.")
                    self.ip_to_id_map = {}
                else:
                    # Create the dictionary mapping {ip_address: id}
                    self.ip_to_id_map = dict(zip(ip_map_df["ip_address"], ip_map_df["id"]))
                    logger.info(f"Successfully loaded {len(self.ip_to_id_map)} IP-to-ID mappings into memory.")

                return True

        except exc.SQLAlchemyError as e:
            logger.exception(f"Database error during IP mapping load: {e}")
            return False
        except Exception as e:
            logger.exception(f"An unexpected error occurred during IP mapping load: {e}")
            return False

    def _load_session_hash_to_ip_id_mapping(self) -> bool:
        """
        Loads the Session Hash to IP ID mapping by joining 'conversations'
        with the loaded 'ip_to_id_map'.
        Requires `_load_ip_to_id_mapping` to be successfully run first.
        """
        self._ensure_engine()
        logger.info("Loading Session Hash-to-IP ID mapping...")

        if not self.ip_to_id_map:
            logger.error("IP-to-ID mapping is not loaded. Cannot create Session Hash-to-IP ID map.")
            return False

        try:
            # Use stream_results for potentially large tables
            query_engine = create_engine(self.database_uri, execution_options={"stream_results": True})
            with query_engine.connect() as conn:
                logger.info("Fetching session_hash and ip from 'conversations' table...")
                # Fetch only necessary columns, filter out nulls early if possible
                query = "SELECT session_hash, ip FROM conversations WHERE session_hash IS NOT NULL AND ip IS NOT NULL"
                conversations_df = pd.read_sql_query(query, conn)

            if conversations_df.empty:
                logger.warning("No valid session_hash/ip pairs found in 'conversations' table.")
                self.session_hash_to_ip_id_map = {}
                return True # Technically loaded successfully, just empty

            logger.info(f"Fetched {len(conversations_df)} session_hash/ip pairs.")

            # Map IP to its ID using the previously loaded ip_to_id_map
            # Note: This assumes ip_to_id_map keys are the IP strings
            conversations_df['ip_id'] = conversations_df['ip'].map(self.ip_to_id_map)

            # Filter out rows where the IP wasn't found in the map (shouldn't happen if load_ip_mapping ran correctly)
            valid_map_df = conversations_df.dropna(subset=['session_hash', 'ip_id'])
            invalid_count = len(conversations_df) - len(valid_map_df)
            if invalid_count > 0:
                 logger.warning(f"Could not find IP IDs for {invalid_count} session hashes (IPs might be missing from ip_map).")


            # Create the dictionary mapping {session_hash: ip_id}
            # If multiple IPs map to the same session_hash, the last one encountered will be kept.
            # Consider if duplicates need specific handling (e.g., logging warnings, choosing first/last).
            self.session_hash_to_ip_id_map = dict(zip(valid_map_df["session_hash"], valid_map_df["ip_id"]))

            logger.info(f"Successfully loaded {len(self.session_hash_to_ip_id_map)} Session Hash-to-IP ID mappings into memory.")
            return True

        except exc.SQLAlchemyError as e:
            logger.exception(f"Database error during Session Hash mapping load: {e}")
            return False
        except Exception as e:
            logger.exception(f"An unexpected error occurred during Session Hash mapping load: {e}")
            return False

    def get_ip_id_from_ip(self, ip_address: str | None) -> int | None:
        """
        Retrieves the unique ID associated with an IP address from the loaded map.

        Args:
            ip_address: The IP address string.

        Returns:
            The unique integer ID, or None if the IP is not found or input is None.
        """
        if not ip_address:
            return None
        ip_id = self.ip_to_id_map.get(ip_address)
        if ip_id is None:
            logger.debug(f"IP address '{ip_address}' not found in the loaded IP-to-ID map.")
        return ip_id

    def get_ip_id_from_session_hash(self, session_hash: str | None) -> int | None:
        """
        Retrieves the unique IP ID associated with a session hash from the loaded map.

        Args:
            session_hash: The session hash string.

        Returns:
            The unique integer IP ID, or None if the session hash is not found or input is None.
        """
        if not session_hash:
            return None
        ip_id = self.session_hash_to_ip_id_map.get(session_hash)
        if ip_id is None:
            # Use debug level to avoid flooding logs if misses are common/expected
            logger.debug(f"Session hash '{session_hash}' not found in the loaded Session Hash-to-IP ID map.")
        return ip_id

    def fetch_and_transform_data(self, query: str | None = None) -> pd.DataFrame | None:
        """
        Fetches data from a specified database table using a query and applies
        transformations, specifically hashing 'visitor_id' and filling missing
        values using a fallback based on 'session_hash'.

        Requires mappings to be loaded first via `load_mappings()`.

        Args:
            query: The SQL query string to fetch data. If None, an error is raised.

        Returns:
            A pandas DataFrame with transformed data, or None if an error occurs
            or the mappings are not loaded.
        """
        self._ensure_engine()
        if not query:
            logger.error(f"No query provided for fetching data from table.")
            return None

        if not self.ip_to_id_map or not self.session_hash_to_ip_id_map:
             logger.error("Identifier mappings are not loaded. Cannot proceed with data transformation.")
             return None

        logger.info(f"Fetching and transforming data for table...")

        try:
            # Use stream_results for potentially large datasets read into pandas
            query_engine = create_engine(self.database_uri, execution_options={"stream_results": True})
            with query_engine.connect() as conn:
                 logger.info(f"Executing query: {query[:200]}...") # Log start of query
                 df = pd.read_sql_query(sql=text(query), con=conn)
                 logger.info(f"Successfully fetched {len(df)} rows from table.")

            # --- Transformations ---
            if "visitor_id" in df.columns:
                initial_null_visitor_ids = df["visitor_id"].isnull().sum()
                logger.info(f"Found {initial_null_visitor_ids} null values in 'visitor_id' column.")

                logger.info("Hashing existing non-null 'visitor_id' values with MD5...")
                # Apply hashing only to non-null values for efficiency
                non_null_mask = df["visitor_id"].notnull()
                df.loc[non_null_mask, "visitor_id"] = df.loc[non_null_mask, "visitor_id"].apply(self._hash_md5)
                logger.info("Completed hashing existing 'visitor_id' values.")

                if "session_hash" in df.columns:
                    logger.info("Applying fallback for missing 'visitor_id' using 'session_hash'...")

                    # Identify rows where visitor_id is null BUT session_hash is not null
                    fallback_mask = df["visitor_id"].isnull() & df["session_hash"].notnull()
                    num_fallback_candidates = fallback_mask.sum()

                    if num_fallback_candidates > 0:
                        logger.info(f"Attempting fallback for {num_fallback_candidates} rows.")
                        # Get the corresponding session hashes for these rows
                        session_hashes_for_fallback = df.loc[fallback_mask, "session_hash"]

                        # Map these session hashes to their corresponding IP IDs using the preloaded map
                        # map() is generally faster than apply() for this kind of lookup
                        ip_ids = session_hashes_for_fallback.map(self.session_hash_to_ip_id_map)

                        # Identify where the mapping succeeded (ip_id is not NaN/None)
                        valid_ip_id_mask = ip_ids.notnull()
                        num_successful_fallbacks = valid_ip_id_mask.sum()

                        if num_successful_fallbacks > 0:
                            # Create the fallback identifier string: "ip-<ip_id>"
                            # Then hash it using the same MD5 function
                            # Note: Hashing the numeric ID might not be necessary. Could use "ip-{ip_id}" directly
                            # if the system consuming this data can handle it. Sticking to original logic for now.
                            fallback_visitor_ids = "ip-" + ip_ids[valid_ip_id_mask].astype(int).astype(str)
                            hashed_fallback_ids = fallback_visitor_ids.apply(self._hash_md5)

                            # Assign these hashed fallback IDs to the original DataFrame
                            # Ensure indices align correctly when assigning back
                            df.loc[fallback_mask & valid_ip_id_mask, "visitor_id"] = hashed_fallback_ids
                            logger.info(f"Successfully applied fallback for {num_successful_fallbacks} rows using session_hash.")

                        num_failed_fallbacks = num_fallback_candidates - num_successful_fallbacks
                        if num_failed_fallbacks > 0:
                            logger.warning(f"Could not find IP ID mapping for {num_failed_fallbacks} session hashes during fallback.")
                    else:
                        logger.info("No rows required visitor_id fallback based on session_hash.")
                else:
                    logger.warning("Cannot apply session_hash fallback: 'session_hash' column not present in the fetched data.")

                final_null_visitor_ids = df[df["visitor_id"].isnull()]
                logger.info(f"Transformation complete. Final null 'visitor_id': {final_null_visitor_ids}")

            else:
                logger.info("'visitor_id' column not found in the fetched data. Skipping visitor_id transformations.")

            return df

        except exc.SQLAlchemyError as e:
            logger.exception(f"Database error during data fetch/transform for table: {e}")
            return None
        except pd.errors.DatabaseError as e: # Catch pandas specific DB errors too
            logger.exception(f"Pandas database error during data fetch/transform for table: {e}")
            return None
        except KeyError as e:
             logger.exception(f"Missing expected column during transformation for table: {e}")
             return None
        except Exception as e:
            logger.exception(f"An unexpected error occurred during data fetch/transform for table: {e}")
            return None

    def insert_ip_map_result_to_conversations(self):
        """
        Inserts the 'id' from the 'ip_map' table into a new column
        named 'ip_map' in the 'conversations' table, based on matching IP addresses.
        """
        self._ensure_engine()
        logger.info("Starting to insert ip_map result into conversations table...")

        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    # Check if the 'ip_map' column already exists in the 'conversations' table
                    inspector = self.engine.dialect.inspector.from_engine(self.engine)

                    # Update the 'conversations' table with the 'id' from 'ip_map'
                    update_sql = text("""
                        UPDATE conversations AS c
                        SET ip_map = im.id
                        FROM ip_map AS im
                        WHERE c.ip = im.ip_address;
                    """)
                    result = conn.execute(update_sql)
                    logger.info(f"Successfully updated {result.rowcount} rows in 'conversations' with 'ip_map' ID.")

            logger.info("Finished inserting ip_map result into conversations table.")
            return True

        except exc.SQLAlchemyError as e:
            logger.exception(f"Database error during insertion of ip_map result: {e}")
            return False
        except Exception as e:
            logger.exception(f"An unexpected error occurred during insertion of ip_map result: {e}")
            return False

# --- Example Usage ---
if __name__ == "__main__":
    # Load database URI from environment variable
    db_uri = os.getenv("DATABASE_URI")

    if not db_uri:
        logger.error("DATABASE_URI environment variable not set. Exiting.")
        exit(1)

    try:
        # 1. Initialize the processor
        data_processor = DataProcessor(database_uri=db_uri)

        # 2. Load the necessary mappings first
        if not data_processor.load_mappings():
            logger.error("Failed to load necessary mappings. Cannot proceed.")
            exit(1)

        # 3. Insert the ip_map result into the conversations table
        if data_processor.insert_ip_map_result_to_conversations():
            logger.info("Successfully inserted ip_map result into the ip_map column of conversations.")
        else:
            logger.error("Failed to insert ip_map result into the ip_map column of conversations.")

        # 4. Define the query and fetch/transform data for a specific table (optional, for demonstration)
        # Example: Fetch data from 'conversations' table itself or another table
        # Make sure the query selects 'visitor_id' and 'session_hash' if needed
        data_query = "SELECT id, visitor_id, session_hash, ip, ip_map, timestamp FROM conversations;" 

        transformed_df = data_processor.fetch_and_transform_data(
            query=data_query
        )

        # 5. Use the transformed data
        if transformed_df is not None:
            logger.info(f"Successfully processed data for '{table_identifier}'. Shape: {transformed_df.shape}")
            # print(transformed_df.head())
            # Further processing...
        else:
            logger.error(f"Failed to process data for '{table_identifier}'.")

    except (ValueError, ConnectionError) as e:
         logger.error(f"Initialization failed: {e}")
         exit(1)
    except Exception as e:
         logger.exception(f"An unexpected error occurred in the main execution block: {e}")
         exit(1)