import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from ..analytics import promo_analyzer, spike_detector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/promo")
def get_promo(
    store_id: str = Query(...),
    from_dt: str = Query(..., alias="from"),
    to_dt: str = Query(..., alias="to"),
    baseline_days: int = Query(14),
    metric: str = Query("footfall", regex="^(footfall|interactions|zone_dwell)$")
):
    from_datetime = datetime.fromisoformat(from_dt.replace("Z", "+00:00"))
    to_datetime = datetime.fromisoformat(to_dt.replace("Z", "+00:00"))

    result = promo_analyzer.calculate_uplift(
        store_id=store_id,
        from_dt=from_datetime,
        to_dt=to_datetime,
        baseline_days=baseline_days,
        metric=metric
    )

    return result


@router.get("/spikes")
def get_spikes(
    store_id: str = Query(...),
    from_dt: str = Query(..., alias="from"),
    to_dt: str = Query(..., alias="to"),
    metric: str = Query("footfall", regex="^(footfall|interactions)$")
):
    from_datetime = datetime.fromisoformat(from_dt.replace("Z", "+00:00"))
    to_datetime = datetime.fromisoformat(to_dt.replace("Z", "+00:00"))

    spikes = spike_detector.detect_spikes(
        store_id=store_id,
        from_dt=from_datetime,
        to_dt=to_datetime,
        metric=metric,
        threshold_z=2.0
    )

    return {"spikes": spikes}
