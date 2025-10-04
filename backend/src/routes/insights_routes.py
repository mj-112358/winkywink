"""
Insights generation routes using OpenAI.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List
import os
import openai

from ..database.models_production import User, Event
from ..database.connection import get_db
from .auth_routes import get_current_user

router = APIRouter(prefix="/api/insights", tags=["insights"])

# OpenAI Configuration
openai.api_key = os.getenv("OPENAI_API_KEY", "")


# Request/Response Models
class InsightRequest(BaseModel):
    promo_name: str | None = None
    promo_start_date: str | None = None
    promo_end_date: str | None = None
    festival_name: str | None = None
    festival_date: str | None = None


class Insight(BaseModel):
    title: str
    description: str
    type: str  # "trend", "alert", "recommendation"


class InsightsResponse(BaseModel):
    insights: List[Insight]
    generated_at: str


# Routes
@router.post("/generate", response_model=InsightsResponse)
async def generate_insights(
    request: InsightRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate insights using OpenAI based on recent event data.
    """
    store_id = current_user.store_id
    if not store_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not assigned to a store")

    # Gather recent event statistics
    last_7_days = datetime.utcnow() - timedelta(days=7)

    # Daily footfall trend
    daily_footfall = db.query(
        func.date(Event.ts).label('date'),
        func.count(Event.id).label('count')
    ).filter(
        Event.store_id == store_id,
        Event.type == "footfall_in",
        Event.ts >= last_7_days
    ).group_by('date').order_by('date').all()

    # Hourly distribution
    hourly_dist = db.query(
        func.extract('hour', Event.ts).label('hour'),
        func.count(Event.id).label('count')
    ).filter(
        Event.store_id == store_id,
        Event.type == "footfall_in",
        Event.ts >= last_7_days
    ).group_by('hour').all()

    # Shelf interactions
    shelf_interactions = db.query(
        func.count(Event.id)
    ).filter(
        Event.store_id == store_id,
        Event.type == "shelf_interaction",
        Event.ts >= last_7_days
    ).scalar() or 0

    # Prepare context for OpenAI
    context = f"""
Store Analytics Summary (Last 7 Days):

Daily Footfall:
{chr(10).join([f"- {r.date}: {r.count} visitors" for r in daily_footfall])}

Peak Hours:
{chr(10).join([f"- Hour {int(r.hour)}: {r.count} visitors" for r in hourly_dist[:5]])}

Total Shelf Interactions: {shelf_interactions}

"""

    if request.promo_name and request.promo_start_date and request.promo_end_date:
        context += f"\nPromo Active: {request.promo_name} ({request.promo_start_date} to {request.promo_end_date})\n"

    if request.festival_name and request.festival_date:
        context += f"\nUpcoming Festival: {request.festival_name} on {request.festival_date}\n"

    # Call OpenAI API
    if not openai.api_key:
        # Fallback if no API key
        return {
            "insights": [
                {
                    "title": "Peak Hours Identified",
                    "description": f"Your store experiences highest footfall during specific hours. Consider staffing optimization during these times.",
                    "type": "trend"
                },
                {
                    "title": "Shelf Interaction Analysis",
                    "description": f"Detected {shelf_interactions} shelf interactions in the last week. Monitor conversion rates for these zones.",
                    "type": "recommendation"
                }
            ],
            "generated_at": datetime.utcnow().isoformat()
        }

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a retail analytics AI assistant. Generate 3-5 actionable insights based on store data. Return insights in this exact JSON format: [{\"title\": \"...\", \"description\": \"...\", \"type\": \"trend|alert|recommendation\"}]"
                },
                {
                    "role": "user",
                    "content": context
                }
            ],
            temperature=0.7
        )

        # Parse OpenAI response
        insights_text = response.choices[0].message.content

        # Try to parse as JSON
        import json
        try:
            insights_list = json.loads(insights_text)
        except:
            # Fallback parsing
            insights_list = [
                {
                    "title": "AI-Generated Insight",
                    "description": insights_text[:500],
                    "type": "recommendation"
                }
            ]

        return {
            "insights": insights_list,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        print(f"OpenAI API error: {e}")
        # Return fallback insights
        return {
            "insights": [
                {
                    "title": "Analytics Summary",
                    "description": f"Analyzed {len(daily_footfall)} days of footfall data with {shelf_interactions} shelf interactions detected.",
                    "type": "trend"
                }
            ],
            "generated_at": datetime.utcnow().isoformat()
        }
