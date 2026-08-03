from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.responses import envelope

from .service import get_current_product

router = APIRouter(prefix="/products", tags=["商品"])


@router.get("/current")
def current_product(request: Request, db: Session = Depends(get_db)):
    result = get_current_product(db)
    return envelope(request, result.model_dump(by_alias=True))
