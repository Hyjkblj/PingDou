"""商品服务"""
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.domain.models import Product

from .schemas import ProductView


def get_current_product(db: Session) -> ProductView:
    """获取当前可购买的商品"""
    product = db.query(Product).filter(Product.is_active.is_(True)).first()
    if not product:
        raise AppError("PRODUCT_UNAVAILABLE", "暂无可购买的商品", status_code=404)
    return ProductView(
        id=product.id,
        name=product.name,
        price_cents=product.price_cents,
        list_price_cents=product.list_price_cents,
        currency=product.currency,
        source_asset_limit=product.source_asset_limit,
        ai_candidate_count=product.ai_candidate_count,
        edit_window_hours=product.edit_window_hours,
        download_retention_days=product.download_retention_days,
        code_validity_days=product.code_validity_days,
        export_formats=product.export_formats,
        refund_policy_version=product.refund_policy_version,
    )
