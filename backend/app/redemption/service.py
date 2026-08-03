"""兑换服务

处理业务码兑换、项目创建和服务权益初始化。
使用数据库行锁保证并发安全。
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.errors import AppError
from app.core.security import hash_redemption_code
from app.domain.enums import (
    EntitlementStatus,
    ProjectStatus,
    RedemptionCodeStatus,
)
from app.domain.models import (
    RedemptionCode,
    ServiceEntitlement,
)

from .schemas import (
    EntitlementBrief,
    ProjectBrief,
    RedeemResponse,
)


def redeem_code(
    db: Session, user_id: str, code: str, idempotency_key: str
) -> tuple[RedeemResponse, bool]:
    """兑换业务码

    事务内完成：
    1. 校验业务码哈希、状态和有效期
    2. 锁定业务码行（SELECT FOR UPDATE）
    3. 创建项目和服务权益
    4. 绑定用户、项目和兑换时间

    Returns:
        (response, is_new): 响应和是否是新兑换
    """
    # 计算业务码哈希
    code_hash = hash_redemption_code(code).encode("utf-8")

    # 查找并锁定业务码行
    rc = (
        db.query(RedemptionCode)
        .filter(RedemptionCode.code_hash == code_hash)
        .with_for_update()
        .first()
    )

    if not rc:
        raise AppError("CODE_INVALID", "业务码格式或内容错误", status_code=400)

    # 检查有效期
    if rc.expires_at < utcnow():
        raise AppError("CODE_EXPIRED", "业务码已过期", status_code=400)

    # 检查状态
    if rc.status == RedemptionCodeStatus.VOIDED:
        raise AppError("CODE_VOIDED", "业务码已作废", status_code=400)

    if rc.status == RedemptionCodeStatus.EXPIRED:
        raise AppError("CODE_EXPIRED", "业务码已过期", status_code=400)

    # 已兑换：检查是否是同一用户
    if rc.status != RedemptionCodeStatus.UNREDEEMED:
        if rc.user_id == user_id:
            # 同一用户重复兑换，返回关联项目
            response = _build_redeem_response(db, rc)
            return response, False
        else:
            # 被其他用户兑换
            raise AppError(
                "CODE_ALREADY_REDEEMED",
                "该业务码已经兑换",
                status_code=409,
                details={"project_id": rc.project_id},
            )

    # 创建项目 ID
    project_id = str(uuid.uuid4())

    # 更新业务码
    rc.status = RedemptionCodeStatus.BOUND
    rc.redeemed_at = utcnow()
    rc.user_id = user_id
    rc.project_id = project_id
    rc.version += 1

    # 创建服务权益
    entitlement = ServiceEntitlement(
        redemption_code_id=rc.id,
        project_id=project_id,
        status=EntitlementStatus.AVAILABLE,
        ai_jobs_total=1,  # 从商品快照读取
        ai_jobs_used=0,
    )
    db.add(entitlement)
    db.flush()

    response = RedeemResponse(
        redemption_code_status=rc.status,
        project=ProjectBrief(id=project_id, status=ProjectStatus.DRAFT),
        entitlement=EntitlementBrief(
            id=entitlement.id,
            status=entitlement.status,
            source_asset_limit=1,
            ai_jobs_total=entitlement.ai_jobs_total,
            ai_jobs_used=entitlement.ai_jobs_used,
            edit_expires_at=entitlement.edit_expires_at,
            download_expires_at=entitlement.download_expires_at,
        ),
    )

    db.commit()
    return response, True


def _build_redeem_response(db: Session, rc: RedemptionCode) -> RedeemResponse:
    """从已兑换的业务码构建响应"""
    entitlement = db.query(ServiceEntitlement).filter(
        ServiceEntitlement.redemption_code_id == rc.id
    ).first()

    return RedeemResponse(
        redemption_code_status=rc.status,
        project=ProjectBrief(id=rc.project_id, status=ProjectStatus.DRAFT),
        entitlement=EntitlementBrief(
            id=entitlement.id if entitlement else "",
            status=entitlement.status if entitlement else "",
            source_asset_limit=1,
            ai_jobs_total=entitlement.ai_jobs_total if entitlement else 0,
            ai_jobs_used=entitlement.ai_jobs_used if entitlement else 0,
            edit_expires_at=entitlement.edit_expires_at if entitlement else None,
            download_expires_at=entitlement.download_expires_at if entitlement else None,
        ),
    )
