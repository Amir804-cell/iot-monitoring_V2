from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from pydantic import BaseModel
from datetime import datetime
from contextlib import contextmanager

# =======================
# LOGGING & DB CONFIGURATION
# =======================
import logging
# VIGTIGT: Importer nu configure_logging som en funktion fra modulet
from .logging_config import configure_logging, create_logging_table, OperationalError

# Database connection details for QuestDB
DB_CONFIG = {
    "dbname": "qdb",
    "user": "admin",
    "password": "quest",
    "host": "localhost", # Debian host, not container name
    "port": 8812        # QuestDB Postgres port
}

# Kald logningskonfigurationen FØR applikationen starter
try:
    configure_logging(DB_CONFIG)
except OperationalError:
    # Loggeren er initialiseret, men QuestDB er nede, så logs er kun i konsollen.
    logging.getLogger(__name__).error("FATAL: Logging setup failed due to initial QuestDB connection error.")

logger = logging.getLogger(__name__) # Opret en logger til dette modul

app = FastAPI()

# CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # in production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =======================
# METRIC DEFINITIONS
# =======================

METRIC_DEFS = [
    ("heat_exchanger_efficiency", "%"),
    ("run_mode", "mode"),

    ("outdoor_temp", "°C"),
    ("supply_air_temp", "°C"),
    ("supply_air_setpoint_temp", "°C"),
    ("exhaust_air_temp", "°C"),
    ("extract_air_temp", "°C"),

    ("supply_air_pressure", "Pa"),
    ("extract_air_pressure", "Pa"),

    ("supply_air_flow", "m³/h"),
    ("extract_air_flow", "m³/h"),
    ("extra_supply_air_flow", "m³/h"),
    ("extra_extract_air_flow", "m³/h"),

    ("supply_air_fan_runtime", "min"),
    ("extract_air_fan_runtime", "min"),
]


class DataQuery(BaseModel):
    device_id: str
    start_time: datetime
    end_time: datetime
    limit: int = 500 # number of rows (each row becomes many metric points)


# =======================
# DATABASE CONNECTION HELPER (Refactored for testability)
# =======================

@contextmanager
def get_db_cursor():
    """
    Establishes a connection to QuestDB, yields the cursor, and handles
    connection closing and error reporting. Used for reading/querying data.
    """
    conn = None
    cur = None
    try:
        logger.debug("Attempting to connect to QuestDB for query...")
        conn = psycopg2.connect(**DB_CONFIG)
        logger.debug("QuestDB connection established.")
        cur = conn.cursor()
        yield cur
        conn.commit()
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed: {str(e)}") # Log fejlen
        raise HTTPException(
            status_code=500, 
            detail=f"Database connection failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}") # Log fejlen
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# =======================
# HELPERS & ENDPOINTS
# =======================

def row_to_metrics(ts, row_values):
    """
    Convert a single DB row (values after ts) to a list of metric dicts.
    """
    metrics = []
    for (name, unit), value in zip(METRIC_DEFS, row_values):
        if value is None:
            continue
        try:
            numeric_value = float(value)
        except Exception:
            numeric_value = value

        metrics.append({
            "metric_name": name,
            "metric_value": numeric_value,
            "unit": unit,
            "timestamp": ts.isoformat()
        })
    return metrics


@app.on_event("startup")
async def startup_event():
    """ Log, når serveren starter, og lav en indledende DB-forbindelse. """
    logger.info("FastAPI server starting up...")
    
    # 1. Opret 'logging' tabellen FØR vi prøver at bruge loggeren
    try:
        create_logging_table(DB_CONFIG)
    except OperationalError:
        # Hvis tabellen ikke kan oprettes, vil logs kun vises i konsollen (DBHandler vil reconnecte)
        logger.warning("QuestDB logging table creation failed. Logs will only appear in console.")
    
    # 2. Tjek om QuestDB er tilgængelig for queries (via get_db_cursor)
    try:
        with get_db_cursor():
            logger.info("Initial QuestDB connection for queries successful.")
    except HTTPException:
        logger.warning("QuestDB is not immediately available for queries; endpoint retries expected.")
    
    logger.info("API startup tasks complete.")


@app.get("/api/devices")
def get_devices():
    """
    Return list of device_ids from olimex_data
    """
    logger.info("Endpoint accessed: /api/devices")
    with get_db_cursor() as cur:
        cur.execute("SELECT DISTINCT device_id FROM olimex_data;")
        devices = [row[0] for row in cur.fetchall()]
        logger.info(f"Found {len(devices)} unique devices.")
        return {"devices": devices}


@app.get("/api/data/latest/{device_id}")
def get_latest_data(device_id: str):
    """
    Return the latest row for a device, converted to a list of metrics.
    """
    logger.info(f"Endpoint accessed: /api/data/latest/{device_id}")
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                ts,
                heat_exchanger_efficiency, run_mode,
                outdoor_temp, supply_air_temp, supply_air_setpoint_temp,
                exhaust_air_temp, extract_air_temp,
                supply_air_pressure, extract_air_pressure,
                supply_air_flow, extract_air_flow,
                extra_supply_air_flow, extra_extract_air_flow,
                supply_air_fan_runtime, extract_air_fan_runtime
            FROM olimex_data
            WHERE device_id = %s
            ORDER BY ts DESC
            LIMIT 1;
            """,
            (device_id,)
        )
        row = cur.fetchone()
        
        if not row:
            logger.warning(f"No data found for device: {device_id}")
            raise HTTPException(status_code=404, detail="No data found for device")

        ts = row[0]
        values = row[1:]

        metrics = row_to_metrics(ts, values)

        return {
            "device_id": device_id,
            "timestamp": ts.isoformat(),
            "data": metrics
        }


@app.post("/api/data/query")
def query_data(data: DataQuery):
    """
    Query historical data for a device and time range from olimex_data.
    """
    logger.info(f"Endpoint accessed: /api/data/query for device {data.device_id}")
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                ts,
                heat_exchanger_efficiency, run_mode,
                outdoor_temp, supply_air_temp, supply_air_setpoint_temp,
                exhaust_air_temp, extract_air_temp,
                supply_air_pressure, extract_air_pressure,
                supply_air_flow, extract_air_flow,
                extra_supply_air_flow, extra_extract_air_flow,
                supply_air_fan_runtime, extract_air_fan_runtime
            FROM olimex_data
            WHERE device_id = %s
              AND ts BETWEEN %s AND %s
            ORDER BY ts ASC
            LIMIT %s;
            """,
            (data.device_id, data.start_time, data.end_time, data.limit)
        )

        rows = cur.fetchall()
        all_metrics = []

        for row in rows:
            ts = row[0]
            values = row[1:]
            all_metrics.extend(row_to_metrics(ts, values))
        
        logger.info(f"Query returned {len(rows)} database rows.")
        return {"data": all_metrics}


@app.get("/")
def root():
    logger.info("Endpoint accessed: /")
    return {"status": "Backend running", "table": "olimex_data"}
