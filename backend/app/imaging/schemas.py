from typing import Any, Literal

from pydantic import Field

from app.core.schemas import AppSchema


class ImageAnalysisRequest(AppSchema):
    project_id: str
    source_asset_id: str


class BackgroundRemovalRequest(AppSchema):
    project_id: str
    source_asset_id: str
    strength: Literal["PRESERVE", "STANDARD", "STRONG"] = "STANDARD"


class CropParams(AppSchema):
    x: float = Field(0, ge=0, le=1)
    y: float = Field(0, ge=0, le=1)
    width: float = Field(1, gt=0, le=1)
    height: float = Field(1, gt=0, le=1)
    rotation: float = 0
    flip_x: bool = False
    flip_y: bool = False


class BackgroundParams(AppSchema):
    mode: str
    palette_color_id: str | None = None


class BaseImagePreviewRequest(AppSchema):
    source_asset_id: str
    foreground_asset_id: str | None = None
    mask_asset_id: str | None = None
    crop: CropParams = Field(default_factory=CropParams)
    background: BackgroundParams


class BaseImageConfirmRequest(AppSchema):
    base_image_preview_id: str


class AiConstraints(AppSchema):
    target_grid: dict[str, int]
    bead_size_mm: float = 5
    palette_id: str
    palette_version: str
    max_colors: int = Field(24, ge=2, le=64)
    outline_protection: str = "STANDARD"


class AiGenerationRequest(AppSchema):
    project_id: str
    source_asset_id: str
    mask_asset_id: str | None = None
    style: str = "ANIME"
    similarity: str = "HIGH"
    detail_level: str = "STANDARD"
    composition: str = "PORTRAIT"
    background_mode: str = "WHITE_PREVIEW"
    constraints: AiConstraints
    candidate_count: int = 2
    addon_entitlement_id: str | None = None


class BaseImageVersionView(AppSchema):
    id: str
    project_id: str
    source_asset_id: str
    foreground_asset_id: str | None = None
    mask_asset_id: str | None = None
    preview_asset: dict[str, Any]
    crop: dict[str, Any]
    background_mode: str
    background_palette_color_id: str | None = None
    confirmed_at: Any
