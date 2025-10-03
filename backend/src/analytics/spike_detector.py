import os
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


def get_database_url():
    return os.getenv("DATABASE_URL", "postgresql://wink_user:password@localhost:5432/wink_analytics")


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def detect_spikes(
    store_id: str,
    from_dt: datetime,
    to_dt: datetime,
    metric: str = "footfall",
    threshold_z: float = 2.0
) -> List[Dict]:
    db = SessionLocal()
    try:
        if metric == "footfall":
            query = text("""
                SELECT DATE(ts) AS day, COUNT(*) AS value
                FROM events
                WHERE store_id = :store_id
                  AND type = 'entrance'
                  AND payload->>'direction' = 'in'
                  AND ts BETWEEN :from_dt AND :to_dt
                GROUP BY 1
                ORDER BY 1
            """)
        elif metric == "interactions":
            query = text("""
                SELECT DATE(ts) AS day, COUNT(*) AS value
                FROM events
                WHERE store_id = :store_id
                  AND type = 'shelf'
                  AND payload->>'state' = 'dwell'
                  AND ts BETWEEN :from_dt AND :to_dt
                GROUP BY 1
                ORDER BY 1
            """)
        else:
            return []

        result = db.execute(query, {"store_id": store_id, "from_dt": from_dt, "to_dt": to_dt})
        rows = result.fetchall()

        if len(rows) < 3:
            return []

        values = [float(row.value) for row in rows]
        mean_val = statistics.mean(values)
        stddev_val = statistics.stdev(values) if len(values) > 1 else 0.0

        if stddev_val == 0:
            return []

        spikes = []
        for row in rows:
            z_score = (row.value - mean_val) / stddev_val
            if abs(z_score) >= threshold_z:
                spikes.append({
                    "date": str(row.day),
                    "metric": metric,
                    "value": row.value,
                    "z_score": round(z_score, 2),
                    "mean": round(mean_val, 2),
                    "stddev": round(stddev_val, 2)
                })

        return spikes
    finally:
        db.close()
