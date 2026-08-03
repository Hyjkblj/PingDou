from app.core.schemas import AppSchema


class ProductView(AppSchema):
    id: str
    name: str
    price_cents: int
    list_price_cents: int
    currency: str
    source_asset_limit: int
    ai_candidate_count: int
    edit_window_hours: int
    download_retention_days: int
    code_validity_days: int
    export_formats: list[str]
    refund_policy_version: str
