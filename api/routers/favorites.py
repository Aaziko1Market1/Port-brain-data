"""
Favorites Router
=================
Endpoints for managing user favorites (buyers, suppliers, products).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from api.deps import get_db
from etl.db_utils import DatabaseManager

router = APIRouter(prefix="/api/v1/favorites", tags=["Favorites"])
logger = logging.getLogger(__name__)


class FavoriteItem(BaseModel):
    """Single favorite item."""
    id: str
    item_type: str
    item_uuid: str
    item_name: Optional[str] = None
    item_country: Optional[str] = None
    added_at: Optional[str] = None


class FavoritesResponse(BaseModel):
    """Response for favorites list."""
    items: List[FavoriteItem]
    total: int


class FavoriteCheckResponse(BaseModel):
    """Response for checking if item is favorited."""
    is_favorite: bool
    item_type: str
    item_uuid: str


@router.get("", response_model=FavoritesResponse)
def list_favorites(
    item_type: Optional[str] = Query(None, description="Filter by type: buyer, supplier, product"),
    limit: int = Query(50, ge=1, le=200),
    db: DatabaseManager = Depends(get_db)
):
    """
    List user favorites.
    
    Returns empty list for now - favorites feature requires user auth.
    """
    return FavoritesResponse(items=[], total=0)


@router.get("/check/{item_type}/{item_uuid}", response_model=FavoriteCheckResponse)
def check_favorite(
    item_type: str,
    item_uuid: str,
    db: DatabaseManager = Depends(get_db)
):
    """
    Check if an item is in favorites.
    
    Returns false for now - favorites feature requires user auth.
    """
    return FavoriteCheckResponse(
        is_favorite=False,
        item_type=item_type,
        item_uuid=item_uuid
    )
