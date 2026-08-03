from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.middleware import require_auth
from app.core.responses import envelope

from .schemas import (
    RefreshTokenRequest,
    SendSmsRequest,
    SmsLoginRequest,
)
from .service import (
    get_current_user,
    login_with_sms,
    refresh_token,
    send_sms_code,
)

router = APIRouter(prefix="/auth", tags=["鉴权"])


@router.post("/sms/send")
def send_sms(request: Request, body: SendSmsRequest, db: Session = Depends(get_db)):
    result = send_sms_code(db, body.phone, body.scene)
    return envelope(request, result.model_dump(by_alias=True))


@router.post("/sms/login")
def sms_login(request: Request, body: SmsLoginRequest, db: Session = Depends(get_db)):
    result = login_with_sms(db, body.phone, body.code)
    return envelope(request, result.model_dump(by_alias=True))


@router.post("/refresh")
def refresh(request: Request, body: RefreshTokenRequest, db: Session = Depends(get_db)):
    result = refresh_token(db, body.refresh_token)
    return envelope(request, result.model_dump(by_alias=True))


@router.get("/users/me")
def users_me(request: Request, user_id: str = Depends(require_auth), db: Session = Depends(get_db)):
    result = get_current_user(db, user_id)
    return envelope(request, result.model_dump(by_alias=True))
