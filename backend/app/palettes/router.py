from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.responses import envelope

from .service import list_colors, list_palettes

router = APIRouter(prefix="/palettes", tags=["色板"])


@router.get("")
def palettes(
    request: Request,
    brand: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    result = list_palettes(db, brand, status)
    return envelope(request, [item.model_dump(by_alias=True) for item in result])


@router.get("/{palette_id}/colors")
def colors(
    request: Request,
    palette_id: str,
    version: str | None = None,
    db: Session = Depends(get_db),
):
    result = list_colors(db, palette_id, version)
    return envelope(request, [item.model_dump(by_alias=True) for item in result])
