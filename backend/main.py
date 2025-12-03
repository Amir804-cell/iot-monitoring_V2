from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from pydantic import BaseModel
from datetime import datetime
from contextlib import contextmanager

app = FastAPI()

# CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =======================
# METRIC DEFINITIONS
# (name + unit)
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
    limit: int = 500  # number of rows (each row becomes many metric points)


# =======================
# DATABASE CONNECTION HELPER (Refactored for testability)
# =======================

@contextmanager
def get_db_cursor():
    """
    Establishes a connection to QuestDB, yields the cursor, and handles
    connection closing and error reporting. This function is now the single
    point of connection and is easily mockable.
    """
    conn = None
    cur = None
    try:
        # >>> CHANGE HERE if your QuestDB credentials differ
        conn = psycopg2.connect(
            dbname="qdb",
            user="admin",
            password="quest",
            host="localhost",    # Debian host, not container name
            port=8812            # QuestDB Postgres port
        )
        cur = conn.cursor()
        yield cur
        conn.commit() # Commit transaction if successful (though reads don't strictly need it)
    except psycopg2.OperationalError as e:
        # Specifically catch connection failures and raise as 500 HTTPException
        raise HTTPException(
            status_code=500, 
            detail=f"Database connection failed: {str(e)}"
        )
    except Exception as e:
        # General database operation error handling (e.g., query execution failure)
        if conn:
            conn.rollback()
        # Raise generic 500 for other unexpected errors
        raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# =======================
# HELPERS
# =======================

def row_to_metrics(ts, row_values):
    """
    Convert a single DB row (values after ts) to a list of metric dicts
    in the shape expected by webserver/index.html:

    {
      "metric_name": "...",
      "metric_value": ...,
      "unit": "...",
      "timestamp": "ISO8601"
    }
    """
    metrics = []
    for (name, unit), value in zip(METRIC_DEFS, row_values):
        if value is None:
            continue
        # run_mode, runtimes etc can be int; Grafana/JS like floats
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


# =======================
# API ENDPOINTS (Updated to use get_db_cursor context manager)
# =======================

@app.get("/api/devices")
def get_devices():
    """
    Return list of device_ids from olimex_data
    -> { "devices": ["OLIMEX_POE", ...] }
    """
    # Using the context manager to automatically open/close the connection
    with get_db_cursor() as cur:
        cur.execute("SELECT DISTINCT device_id FROM olimex_data;")
        devices = [row[0] for row in cur.fetchall()]
        return {"devices": devices}


@app.get("/api/data/latest/{device_id}")
def get_latest_data(device_id: str):
    """
    Return the latest row for a device, converted to a list of metrics.
    """
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

        return {"data": all_metrics}


@app.get("/")
def root():
    return {"status": "Backend running", "table": "olimex_data"}
