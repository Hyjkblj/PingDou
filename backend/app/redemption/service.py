"""Transactional redemption of a one-time service code."""

from sqlalchemy.orm import Session

from app.core.db import is_past, utcnow
from app.core.errors import AppError
from app.core.security import hash_redemption_code
from app.domain.enums import EntitlementStatus, ProjectStatus, RedemptionCodeStatus
from app.domain.models import (
    EntitlementEvent,
    Order,
    Project,
    RedemptionCode,
    ServiceEntitlement,
)

from .schemas import EntitlementBrief, ProjectBrief, RedeemResponse


def redeem_code(
    db: Session, user_id: str, code: str, idempotency_key: str
) -> tuple[RedeemResponse, bool]:
    code_hash = hash_redemption_code(code).encode("utf-8")
    redemption = (
        db.query(RedemptionCode)
        .filter(RedemptionCode.code_hash == code_hash)
        .with_for_update()
        .first()
    )
    if not redemption:
        raise AppError("CODE_INVALID", "业务码格式或内容错误", status_code=400)
    if is_past(redemption.expires_at):
        redemption.status = RedemptionCodeStatus.EXPIRED
        db.commit()
        raise AppError("CODE_EXPIRED", "业务码已过期", status_code=400)
    if redemption.status == RedemptionCodeStatus.VOIDED:
        raise AppError("CODE_VOIDED", "业务码已作废", status_code=400)
    if redemption.status == RedemptionCodeStatus.EXPIRED:
        raise AppError("CODE_EXPIRED", "业务码已过期", status_code=400)
    if redemption.status != RedemptionCodeStatus.UNREDEEMED:
        if redemption.user_id == user_id:
            return _build_redeem_response(db, redemption), False
        raise AppError(
            "CODE_ALREADY_REDEEMED",
            "该业务码已经兑换",
            status_code=409,
        )

    order = db.query(Order).filter(Order.id == redemption.order_id).first()
    snapshot = order.product_snapshot if order else {}
    project = Project(
        user_id=user_id,
        name=snapshot.get("name", "未命名拼豆项目"),
        status=ProjectStatus.DRAFT,
    )
    db.add(project)
    db.flush()
    entitlement = ServiceEntitlement(
        redemption_code_id=redemption.id,
        project_id=project.id,
        status=EntitlementStatus.AVAILABLE,
        source_asset_limit=snapshot.get("source_asset_limit", 1),
        ai_jobs_total=snapshot.get("ai_jobs_total", 1),
        ai_jobs_used=0,
    )
    db.add(entitlement)
    db.flush()
    redemption.status = RedemptionCodeStatus.BOUND
    redemption.redeemed_at = utcnow()
    redemption.user_id = user_id
    redemption.project_id = project.id
    redemption.code_ciphertext = None
    redemption.version += 1
    db.add(
        EntitlementEvent(
            entitlement_id=entitlement.id,
            event_type="CODE_REDEEMED",
            payload={"projectId": project.id, "idempotencyKey": idempotency_key},
        )
    )
    db.commit()
    return _build_redeem_response(db, redemption), True


def _build_redeem_response(db: Session, redemption: RedemptionCode) -> RedeemResponse:
    entitlement = db.query(ServiceEntitlement).filter(
        ServiceEntitlement.redemption_code_id == redemption.id
    ).first()
    project = db.query(Project).filter(Project.id == redemption.project_id).first()
    if not entitlement or not project:
        raise AppError("ENTITLEMENT_UNAVAILABLE", "服务权益不可用", status_code=403)
    return RedeemResponse(
        redemption_code_status=redemption.status,
        project=ProjectBrief(id=project.id, status=project.status),
        entitlement=EntitlementBrief(
            id=entitlement.id,
            status=entitlement.status,
            source_asset_limit=entitlement.source_asset_limit,
            ai_jobs_total=entitlement.ai_jobs_total,
            ai_jobs_used=entitlement.ai_jobs_used,
            edit_expires_at=entitlement.edit_expires_at,
            download_expires_at=entitlement.download_expires_at,
        ),
    )
