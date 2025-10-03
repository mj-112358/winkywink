import os
import logging
from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


def get_database_url():
    return os.getenv("DATABASE_URL", "postgresql://wink_user:password@localhost:5432/wink_analytics")


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def calculate_uplift(
    store_id: str,
    from_dt: datetime,
    to_dt: datetime,
    baseline_days: int = 14,
    metric: str = "footfall"
) -> Dict:
    db = SessionLocal()
    try:
        promo_duration = (to_dt - from_dt).total_seconds() / 86400

        baseline_start = from_dt - timedelta(days=baseline_days)
        baseline_end = from_dt - timedelta(seconds=1)

        if metric == "footfall":
            promo_val = db.execute(text("""
                SELECT COUNT(*) FROM events
                WHERE store_id = :store_id
                  AND type = 'entrance'
                  AND payload->>'direction' = 'in'
                  AND ts BETWEEN :from_dt AND :to_dt
            """), {"store_id": store_id, "from_dt": from_dt, "to_dt": to_dt}).scalar() or 0

            baseline_val = db.execute(text("""
                SELECT COUNT(*) FROM events
                WHERE store_id = :store_id
                  AND type = 'entrance'
                  AND payload->>'direction' = 'in'
                  AND ts BETWEEN :baseline_start AND :baseline_end
            """), {"store_id": store_id, "baseline_start": baseline_start, "baseline_end": baseline_end}).scalar() or 0

        elif metric == "interactions":
            promo_val = db.execute(text("""
                SELECT COUNT(*) FROM events
                WHERE store_id = :store_id
                  AND type = 'shelf'
                  AND payload->>'state' = 'dwell'
                  AND ts BETWEEN :from_dt AND :to_dt
            """), {"store_id": store_id, "from_dt": from_dt, "to_dt": to_dt}).scalar() or 0

            baseline_val = db.execute(text("""
                SELECT COUNT(*) FROM events
                WHERE store_id = :store_id
                  AND type = 'shelf'
                  AND payload->>'state' = 'dwell'
                  AND ts BETWEEN :baseline_start AND :baseline_end
            """), {"store_id": store_id, "baseline_start": baseline_start, "baseline_end": baseline_end}).scalar() or 0

        elif metric == "zone_dwell":
            promo_val = db.execute(text("""
                SELECT AVG((payload->>'dwell_sec')::float) FROM events
                WHERE store_id = :store_id
                  AND type = 'zone'
                  AND payload->>'state' = 'exit'
                  AND ts BETWEEN :from_dt AND :to_dt
            """), {"store_id": store_id, "from_dt": from_dt, "to_dt": to_dt}).scalar() or 0

            baseline_val = db.execute(text("""
                SELECT AVG((payload->>'dwell_sec')::float) FROM events
                WHERE store_id = :store_id
                  AND type = 'zone'
                  AND payload->>'state' = 'exit'
                  AND ts BETWEEN :baseline_start AND :baseline_end
            """), {"store_id": store_id, "baseline_start": baseline_start, "baseline_end": baseline_end}).scalar() or 0

        else:
            return {"error": f"Unknown metric: {metric}"}

        promo_daily = promo_val / promo_duration if promo_duration > 0 else 0
        baseline_daily = baseline_val / baseline_days if baseline_days > 0 else 0

        uplift_percent = 0.0
        if baseline_daily > 0:
            uplift_percent = ((promo_daily - baseline_daily) / baseline_daily) * 100

        return {
            "metric": metric,
            "promo_period": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "baseline_period": {"from": baseline_start.isoformat(), "to": baseline_end.isoformat()},
            "promo_value": round(promo_val, 2),
            "baseline_value": round(baseline_val, 2),
            "promo_daily": round(promo_daily, 2),
            "baseline_daily": round(baseline_daily, 2),
            "uplift_percent": round(uplift_percent, 2)
        }
    finally:
        db.close()
