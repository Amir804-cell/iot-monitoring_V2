import logging
import sys
import psycopg2
from psycopg2 import OperationalError

# Define the QuestDB table schema for persistent logging
LOGGING_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS logging (
    ts TIMESTAMP,
    level STRING,
    logger STRING,
    message STRING
) timestamp(ts) PARTITION BY DAY;
"""

def create_logging_table(db_config: dict):
    """
    Ensures the 'logging' table exists in QuestDB.
    """
    logger = logging.getLogger(__name__)
    conn = None
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute(LOGGING_TABLE_SCHEMA)
        conn.commit()
        cur.close()
        logger.info("QuestDB 'logging' table verified/created successfully.")
    except OperationalError as e:
        logger.error(f"Failed to connect to QuestDB to create logging table: {e}")
        # Re-raise to prevent application startup if DB is totally unavailable
        raise
    finally:
        if conn:
            conn.close()

class QuestDBHandler(logging.Handler):
    """
    A custom logging handler that sends log records to QuestDB.
    """
    def __init__(self, db_config: dict, level=logging.NOTSET):
        super().__init__(level)
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        self.logger_name = logging.getLogger(__name__).name # Use internal logger for handler messages
        self._connect()

    def _connect(self):
        """ Establish and store a database connection for the handler. """
        try:
            if self.conn and not self.conn.closed:
                self.cursor.close()
                self.conn.close()
            
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor()
        except OperationalError:
            # If DB is not available, the handler should fail silently during normal operation,
            # but log to stderr/console so the user knows.
            sys.stderr.write(f"[{self.logger_name}] WARNING: QuestDBHandler failed to connect to database.\n")
            self.conn = None
            self.cursor = None
        except Exception as e:
            sys.stderr.write(f"[{self.logger_name}] ERROR during QuestDBHandler setup: {e}\n")
            self.conn = None
            self.cursor = None

    def emit(self, record):
        """
        Emit a record by inserting it into the QuestDB 'logging' table.
        
        Uses casting (::TIMESTAMP) and %s placeholders for psycopg2 compatibility.
        """
        # Ensure we have a valid connection before attempting to write
        if not self.conn or self.conn.closed or not self.cursor:
            self._connect() # Attempt to reconnect
            if not self.conn:
                return # Give up if reconnection fails
        
        # ts (timestamp) must be in microseconds for QuestDB
        ts_microseconds = int(record.created * 1_000_000) + record.msecs * 1000
        
        # --- KORRIGERET SQL HER: Bruger %s pladsholdere ---
        insert_sql = """
        INSERT INTO logging(ts, level, logger, message)
        VALUES (%s::TIMESTAMP, %s, %s, %s)
        """
        
        try:
            # Rækkefølgen af parametre svarer til %s i insert_sql
            self.cursor.execute(insert_sql, (
                ts_microseconds,
                record.levelname,
                record.name,
                record.message
            ))
            self.conn.commit()
        except Exception as e:
            # Fallback to console if DB writing fails mid-operation
            sys.stderr.write(f"[{self.logger_name}] ERROR writing log to QuestDB: {e}. Log: {record.message}\n")
            if self.conn:
                self.conn.rollback() # Rollback the failed transaction
            self._connect() # Attempt to reconnect for the next log entry

# Dette er nu en selvstændig funktion, som den skal være
def configure_logging(db_config: dict):
    """
    Configure structured logging for the FastAPI backend,
    attaching both StreamHandler and QuestDBHandler.
    """
    root = logging.getLogger()
    
    # CRITICAL: Prevent setting up logging multiple times, which duplicates logs.
    if root.handlers:
        return

    # 1. Console Handler (Standard SPDLog format to console/stderr)
    handler = logging.StreamHandler(sys.stderr)
    fmt = "[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    handler.setFormatter(formatter)
    root.addHandler(handler)
    
    # 2. QuestDB Handler (Custom persistence)
    db_handler = QuestDBHandler(db_config)
    # We attach the stream formatter to the DB handler for consistency
    db_handler.setFormatter(formatter) 
    root.addHandler(db_handler)

    # Set the base logging level (e.g., INFO, DEBUG, WARNING)
    root.setLevel(logging.INFO)
    
    # Suppress redundant or excessively verbose logs from external libraries 
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Log successful configuration using the configured logger
    logging.getLogger(__name__).info("Custom logging initialized with SPDLog style format and QuestDB persistence.")
