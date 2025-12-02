"""
EPIC 7C - AI Co-Pilot Router
==============================
AI-powered explanation and analysis endpoints.

All AI responses are generated from structured data context only.
The LLM never has direct database access.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID

from api.deps import get_db
from api.llm import get_llm_client, detect_llm_capabilities, detect_llm
from api.llm.client import get_llm_status, DisabledLLMClient
from etl.db_utils import DatabaseManager

router = APIRouter(prefix="/api/v1/ai", tags=["AI Co-Pilot"])
logger = logging.getLogger(__name__)


# Response models
class AIExplanationResponse(BaseModel):
    """AI-generated explanation response."""
    explanation: str
    provider: Optional[str] = None
    model: Optional[str] = None


class AIStatusResponse(BaseModel):
    """AI Co-Pilot status."""
    available: bool
    provider: Optional[str] = None
    model: Optional[str] = None
    message: str
    reason: Optional[str] = None


class AskQuestionRequest(BaseModel):
    """Request for asking a question about a buyer."""
    question: str


def _safe_float(value) -> Optional[float]:
    """Safely convert to float."""
    if value is None:
        return None
    try:
        import math
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except:
        return None


def _parse_jsonb(value) -> list:
    """Parse JSONB value."""
    import json
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except:
            return []
    if isinstance(value, list):
        return value
    return []


def _fetch_buyer_context(db: DatabaseManager, buyer_uuid: str) -> Dict[str, Any]:
    """
    Fetch comprehensive buyer context for AI.
    
    Returns structured JSON with buyer profile, risk, and activity data.
    """
    # Fetch from vw_buyer_360
    query = """
        SELECT 
            buyer_uuid::text,
            buyer_name,
            buyer_country,
            buyer_classification,
            total_shipments,
            total_value_usd,
            total_qty_kg,
            total_teu,
            first_shipment_date,
            last_shipment_date,
            active_years,
            unique_hs_codes,
            unique_origin_countries,
            unique_suppliers,
            top_hs6,
            top_origin_countries,
            current_risk_level,
            current_risk_score,
            current_confidence_score,
            current_main_reason_code,
            has_ghost_flag,
            risk_engine_version,
            risk_reasons_sample
        FROM vw_buyer_360
        WHERE buyer_uuid = %s::uuid
    """
    
    result = db.execute_query(query, (buyer_uuid,))
    
    if not result:
        return None
    
    row = result[0]
    
    # Parse JSON fields
    top_hs = _parse_jsonb(row[14])
    top_origins = _parse_jsonb(row[15])
    risk_reasons = _parse_jsonb(row[22]) if row[22] else None
    
    context = {
        "buyer": {
            "buyer_uuid": row[0],
            "buyer_name": row[1],
            "buyer_country": row[2],
            "classification": row[3],
            "total_shipments": row[4] or 0,
            "total_value_usd": _safe_float(row[5]),
            "total_qty_kg": _safe_float(row[6]),
            "total_teu": _safe_float(row[7]),
            "first_shipment_date": str(row[8]) if row[8] else None,
            "last_shipment_date": str(row[9]) if row[9] else None,
            "active_years": row[10] or 0,
            "unique_hs_codes": row[11] or 0,
            "unique_origin_countries": row[12] or 0,
            "unique_suppliers": row[13] or 0,
            "top_hs_codes": top_hs[:5] if top_hs else [],
            "top_origin_countries": top_origins[:5] if top_origins else []
        },
        "risk": {
            "risk_level": row[16] or "UNSCORED",
            "risk_score": _safe_float(row[17]),
            "confidence_score": _safe_float(row[18]),
            "main_reason_code": row[19],
            "has_ghost_flag": row[20] or False,
            "engine_version": row[21],
            "reason_details": risk_reasons
        }
    }
    
    # Fetch HS activity summary
    hs_query = """
        SELECT 
            hs_code_6,
            SUM(shipment_count) as shipments,
            SUM(total_value_usd) as value_usd
        FROM vw_buyer_hs_activity
        WHERE buyer_uuid = %s::uuid
        GROUP BY hs_code_6
        ORDER BY value_usd DESC NULLS LAST
        LIMIT 10
    """
    
    try:
        hs_result = db.execute_query(hs_query, (buyer_uuid,))
        context["hs_activity"] = [
            {
                "hs_code_6": row[0],
                "shipments": row[1],
                "value_usd": _safe_float(row[2])
            }
            for row in (hs_result or [])
        ]
    except:
        context["hs_activity"] = []
    
    return context


@router.get("/status", response_model=AIStatusResponse)
def get_ai_status():
    """
    Get AI Co-Pilot availability status.
    
    Returns whether AI features are available and which provider is being used.
    """
    config = detect_llm()
    
    if config.available:
        return AIStatusResponse(
            available=True,
            provider=config.provider,
            model=config.model,
            message=f"AI Co-Pilot active using {config.provider} / {config.model}",
            reason=config.reason
        )
    else:
        return AIStatusResponse(
            available=False,
            provider=None,
            model=None,
            message="AI Co-Pilot unavailable. Configure an LLM provider to enable AI features.",
            reason=config.reason
        )


@router.post("/explain-buyer/{buyer_uuid}", response_model=AIExplanationResponse)
def explain_buyer(
    buyer_uuid: str,
    use_case: str = Query(
        "sales",
        description="Use case: 'sales' for business pitch, 'risk' for due diligence, 'general' for overview"
    ),
    db: DatabaseManager = Depends(get_db)
):
    """
    Generate AI explanation for a buyer.
    
    Fetches buyer data from the database and uses the LLM to generate
    a business-friendly explanation.
    
    The LLM only sees the structured JSON context - it cannot access
    the database directly or invent data.
    """
    # Validate UUID
    try:
        UUID(buyer_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid buyer UUID format")
    
    # Get LLM client
    llm = get_llm_client()
    
    # Check if LLM is available
    if isinstance(llm, DisabledLLMClient):
        raise HTTPException(
            status_code=503,
            detail="AI Co-Pilot unavailable. No LLM provider configured."
        )
    
    # Fetch buyer context
    context = _fetch_buyer_context(db, buyer_uuid)
    
    if not context:
        raise HTTPException(status_code=404, detail=f"Buyer not found: {buyer_uuid}")
    
    # Build prompt based on use case
    if use_case == "sales":
        prompt = """Explain this buyer to a manufacturer looking for potential business partners.
Focus on:
1. Company overview (name, location, scale of operations)
2. Product focus (what HS codes they trade, what products these represent)
3. Volume and value patterns (are they a large or small buyer?)
4. Main trade routes (where do they source from?)
5. Risk assessment and any concerns
6. Business opportunity summary and recommended approach

Use ONLY the data provided. Do not invent any numbers or facts.
Keep the response concise and business-focused."""
    
    elif use_case == "risk":
        prompt = """Analyze this buyer for due diligence purposes.
Focus on:
1. Risk level and score interpretation
2. Specific risk factors identified
3. What the risk signals mean
4. Trade pattern analysis (any unusual patterns?)
5. Recommended verification steps
6. Overall risk assessment summary

Use ONLY the data provided. Be factual and specific."""
    
    else:  # general
        prompt = """Provide a general overview of this buyer.
Include:
1. Who they are (name, country, classification)
2. Their trade activity (shipments, value, products)
3. Main suppliers and routes
4. Current risk status
5. Key insights

Use ONLY the data provided. Be concise."""
    
    try:
        # Generate explanation
        explanation = llm.generate(prompt, context=context)
        
        # Get provider info
        status = get_llm_status()
        
        return AIExplanationResponse(
            explanation=explanation,
            provider=status.get("provider"),
            model=status.get("model")
        )
        
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI generation failed: {str(e)}"
        )


@router.post("/ask-buyer/{buyer_uuid}", response_model=AIExplanationResponse)
def ask_about_buyer(
    buyer_uuid: str,
    request: AskQuestionRequest,
    db: DatabaseManager = Depends(get_db)
):
    """
    Ask a specific question about a buyer.
    
    The AI will answer using only the buyer's data context.
    """
    # Validate UUID
    try:
        UUID(buyer_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid buyer UUID format")
    
    # Get LLM client
    llm = get_llm_client()
    
    if isinstance(llm, DisabledLLMClient):
        raise HTTPException(
            status_code=503,
            detail="AI Co-Pilot unavailable. No LLM provider configured."
        )
    
    # Fetch context
    context = _fetch_buyer_context(db, buyer_uuid)
    
    if not context:
        raise HTTPException(status_code=404, detail=f"Buyer not found: {buyer_uuid}")
    
    try:
        explanation = llm.answer_question(request.question, context)
        status = get_llm_status()
        
        return AIExplanationResponse(
            explanation=explanation,
            provider=status.get("provider"),
            model=status.get("model")
        )
        
    except Exception as e:
        logger.error(f"LLM question answering failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI generation failed: {str(e)}"
        )


@router.get("/capabilities")
def get_ai_capabilities():
    """
    Get detailed AI capabilities and detected providers.
    
    Useful for debugging and understanding what LLM options are available.
    """
    caps = detect_llm_capabilities()
    return caps.to_dict()
