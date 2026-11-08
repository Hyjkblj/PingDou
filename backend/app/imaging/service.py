import io

from PIL import Image, ImageOps, ImageStat
from sqlalchemy.orm import Session

from app.assets.service import asset_view, create_derived_asset, require_asset
from app.core.errors import AppError
from app.core.storage import storage
from app.domain.access import require_entitlement
from app.domain.enums import (
    AssetType,
    BackgroundMode,
    JobType,
    ProjectStatus,
)
from app.domain.models import (
    BaseImagePreview,
    BaseImageVersion,
    EntitlementEvent,
    Palette,
    PaletteColor,
    Project,
)
from app.jobs.service import create_job, run_eager_job, to_job_view

from .provider import image_provider
from .schemas import (
    AiGenerationRequest,
    BackgroundRemovalRequest,
    BaseImageConfirmRequest,
    BaseImagePreviewRequest,
    BaseImageVersionView,
    ImageAnalysisRequest,
)


def create_analysis_job(
    db: Session, user_id: str, body: ImageAnalysisRequest, idempotency_key: str
):
    require_entitlement(db, user_id, body.project_id)
    asset = require_asset(db, user_id, body.source_asset_id, body.project_id)
    job, created = create_job(
        db,
        user_id=user_id,
        project_id=body.project_id,
        job_type=JobType.IMAGE_ANALYSIS,
        idempotency_key=idempotency_key,
        initial_stage="ANALYZING_IMAGE",
    )
    if created:
        def worker():
            image = Image.open(storage.path(asset.storage_key)).convert("RGB")
            stat = ImageStat.Stat(image.resize((64, 64)))
            contrast = sum(stat.stddev) / 3
            score = max(30, min(96, round(55 + contrast * 0.8)))
            issues = []
            if contrast > 55:
                issues.append(
                    {
                        "code": "BACKGROUND_COMPLEX",
                        "severity": "MEDIUM",
                        "message": "背景颜色和纹理较复杂",
                    }
                )
            recommendation = "DIRECT" if score >= 80 else "AI_RECOMMENDED"
            return {
                "suitabilityScore": score,
                "recommendation": recommendation,
                "issues": issues,
                "suggestedActions": (
                    []
                    if recommendation == "DIRECT"
                    else ["BACKGROUND_REMOVAL", "CARTOONIZE"]
                ),
            }

        run_eager_job(db, job, worker, failure_code="IMAGE_ANALYSIS_FAILED")
        project = db.query(Project).filter(Project.id == body.project_id).first()
        if project:
            project.status = ProjectStatus.BASE_IMAGE_PENDING
            db.commit()
    db.refresh(job)
    return to_job_view(job), created


def create_background_removal_job(
    db: Session, user_id: str, body: BackgroundRemovalRequest, idempotency_key: str
):
    require_entitlement(db, user_id, body.project_id)
    source = require_asset(db, user_id, body.source_asset_id, body.project_id)
    job, created = create_job(
        db,
        user_id=user_id,
        project_id=body.project_id,
        job_type=JobType.BACKGROUND_REMOVAL,
        idempotency_key=idempotency_key,
        initial_stage="REMOVING_BACKGROUND",
    )
    if created:
        def worker():
            result = image_provider.remove_background(
                storage.read(source.storage_key), body.strength
            )
            foreground = create_derived_asset(
                db,
                user_id=user_id,
                project_id=body.project_id,
                asset_type=AssetType.FOREGROUND_IMAGE,
                file_name="foreground.png",
                mime_type="image/png",
                content=result.foreground_png,
                width=result.width,
                height=result.height,
            )
            mask = create_derived_asset(
                db,
                user_id=user_id,
                project_id=body.project_id,
                asset_type=AssetType.SUBJECT_MASK,
                file_name="subject-mask.png",
                mime_type="image/png",
                content=result.mask_png,
                width=result.width,
                height=result.height,
            )
            white_preview = create_derived_asset(
                db,
                user_id=user_id,
                project_id=body.project_id,
                asset_type=AssetType.WHITE_PREVIEW,
                file_name="white-preview.png",
                mime_type="image/png",
                content=result.white_preview_png,
                width=result.width,
                height=result.height,
            )
            db.commit()
            for item in (foreground, mask, white_preview):
                db.refresh(item)
            return {
                "foregroundAsset": asset_view(foreground).model_dump(by_alias=True),
                "maskAsset": asset_view(mask).model_dump(by_alias=True),
                "whitePreviewAsset": asset_view(white_preview).model_dump(by_alias=True),
                "edgeQualityScore": result.edge_quality_score,
                "suggestedCrop": {"x": 0.05, "y": 0.05, "width": 0.9, "height": 0.9},
            }

        run_eager_job(db, job, worker, failure_code="BACKGROUND_REMOVAL_FAILED")
    db.refresh(job)
    return to_job_view(job), created


def create_base_preview(
    db: Session, user_id: str, project_id: str, body: BaseImagePreviewRequest
) -> dict:
    require_entitlement(db, user_id, project_id)
    source = require_asset(db, user_id, body.source_asset_id, project_id)
    foreground = (
        require_asset(db, user_id, body.foreground_asset_id, project_id)
        if body.foreground_asset_id
        else source
    )
    mask = (
        require_asset(db, user_id, body.mask_asset_id, project_id) if body.mask_asset_id else None
    )
    mode = body.background.mode
    solid_modes = {BackgroundMode.SOLID_WHITE_BEADS, BackgroundMode.SOLID_CUSTOM_BEADS}
    transparent_modes = {BackgroundMode.WHITE_PREVIEW, BackgroundMode.TRANSPARENT}
    if mode in solid_modes and not body.background.palette_color_id:
        raise AppError("BACKGROUND_COLOR_REQUIRED", "实体背景缺少色号", status_code=400)
    if mode in transparent_modes and body.background.palette_color_id:
        raise AppError("BACKGROUND_COLOR_NOT_ALLOWED", "该背景模式不能指定色号", status_code=400)
    background_rgb = None
    if body.background.palette_color_id:
        color = db.query(PaletteColor).filter(
            PaletteColor.id == body.background.palette_color_id,
            PaletteColor.enabled.is_(True),
        ).first()
        if not color:
            raise AppError("COLOR_NOT_IN_PALETTE", "背景色号不存在", status_code=400)
        background_rgb = color.rgb
    image = Image.open(storage.path(foreground.storage_key)).convert("RGBA")
    image = _apply_crop(image, body.crop.model_dump())
    if mask:
        mask_image = Image.open(storage.path(mask.storage_key)).convert("L")
        mask_image = _apply_crop(mask_image, body.crop.model_dump()).resize(image.size)
        image.putalpha(mask_image)
    transparent_count = _transparent_grid_count(image, 80, 80)
    if mode == BackgroundMode.WHITE_PREVIEW:
        canvas = Image.new("RGBA", image.size, "white")
        canvas.alpha_composite(image)
        preview_image = canvas.convert("RGB")
        background_beads = 0
    elif mode == BackgroundMode.TRANSPARENT:
        preview_image = image
        background_beads = 0
    elif mode in solid_modes:
        canvas = Image.new("RGBA", image.size, background_rgb or "white")
        canvas.alpha_composite(image)
        preview_image = canvas.convert("RGB")
        background_beads = transparent_count
    else:
        preview_image = Image.open(storage.path(source.storage_key)).convert("RGB")
        background_beads = transparent_count
    content = _image_bytes(preview_image)
    preview_asset = create_derived_asset(
        db,
        user_id=user_id,
        project_id=project_id,
        asset_type=AssetType.WHITE_PREVIEW,
        file_name="base-image-preview.png",
        mime_type="image/png",
        content=content,
        width=preview_image.width,
        height=preview_image.height,
        metadata={"backgroundMode": mode, "backgroundCountsAsBeads": mode in solid_modes},
    )
    preview = BaseImagePreview(
        project_id=project_id,
        source_asset_id=source.id,
        foreground_asset_id=foreground.id if foreground.id != source.id else None,
        mask_asset_id=mask.id if mask else None,
        preview_asset_id=preview_asset.id,
        crop=body.crop.model_dump(by_alias=True),
        background_mode=mode,
        background_palette_color_id=body.background.palette_color_id,
        estimated_background_bead_count=background_beads,
    )
    db.add(preview)
    db.commit()
    db.refresh(preview)
    db.refresh(preview_asset)
    return {
        "id": preview.id,
        "previewAsset": asset_view(preview_asset).model_dump(by_alias=True),
        "backgroundMode": preview.background_mode,
        "backgroundPaletteColorId": preview.background_palette_color_id,
        "estimatedBackgroundBeadCount": preview.estimated_background_bead_count,
        "backgroundCountsAsBeads": mode in solid_modes,
    }


def confirm_base_image(
    db: Session,
    user_id: str,
    project_id: str,
    body: BaseImageConfirmRequest,
) -> tuple[BaseImageVersionView, bool]:
    require_entitlement(db, user_id, project_id)
    preview = db.query(BaseImagePreview).filter(
        BaseImagePreview.id == body.base_image_preview_id,
        BaseImagePreview.project_id == project_id,
    ).first()
    if not preview:
        raise AppError("BASE_IMAGE_PREVIEW_NOT_FOUND", "基底预览不存在", status_code=404)
    existing = db.query(BaseImageVersion).filter(
        BaseImageVersion.preview_id == preview.id
    ).first()
    created = False
    if not existing:
        existing = BaseImageVersion(
            project_id=project_id,
            preview_id=preview.id,
            source_asset_id=preview.source_asset_id,
            foreground_asset_id=preview.foreground_asset_id,
            mask_asset_id=preview.mask_asset_id,
            preview_asset_id=preview.preview_asset_id,
            crop=preview.crop,
            background_mode=preview.background_mode,
            background_palette_color_id=preview.background_palette_color_id,
        )
        db.add(existing)
        db.flush()
        project = db.query(Project).filter(Project.id == project_id).first()
        project.current_base_image_version_id = existing.id
        project.cover_asset_id = existing.preview_asset_id
        project.status = ProjectStatus.PATTERN_PENDING
        db.commit()
        db.refresh(existing)
        created = True
    return _base_version_view(existing), created


def create_ai_job(
    db: Session, user_id: str, body: AiGenerationRequest, idempotency_key: str
):
    entitlement = require_entitlement(db, user_id, body.project_id)
    source = require_asset(db, user_id, body.source_asset_id, body.project_id)
    if body.candidate_count != 2:
        raise AppError("VALIDATION_ERROR", "首期候选图数量固定为 2", status_code=422)
    palette = db.query(Palette).filter(
        Palette.id == body.constraints.palette_id,
        Palette.version == body.constraints.palette_version,
        Palette.status == "ACTIVE",
    ).first()
    if not palette:
        raise AppError("PALETTE_VERSION_NOT_FOUND", "色板版本不存在", status_code=404)
    if entitlement.ai_jobs_used >= entitlement.ai_jobs_total and not body.addon_entitlement_id:
        raise AppError("AI_QUOTA_EXHAUSTED", "已使用包含的 AI 次数", status_code=403)
    job, created = create_job(
        db,
        user_id=user_id,
        project_id=body.project_id,
        job_type=JobType.AI_GENERATION,
        idempotency_key=idempotency_key,
        initial_stage="GENERATING_CANDIDATES",
    )
    if created:
        def worker():
            candidates = image_provider.generate_candidates(
                storage.read(source.storage_key), body.candidate_count
            )
            views = []
            for index, content in enumerate(candidates):
                image = Image.open(io.BytesIO(content))
                asset = create_derived_asset(
                    db,
                    user_id=user_id,
                    project_id=body.project_id,
                    asset_type=AssetType.AI_CANDIDATE,
                    file_name=f"ai-candidate-{index + 1}.png",
                    mime_type="image/png",
                    content=content,
                    width=image.width,
                    height=image.height,
                    metadata={"style": body.style, "candidateIndex": index},
                )
                db.flush()
                views.append(
                    {
                        "id": asset.id,
                        "asset": asset_view(asset).model_dump(by_alias=True),
                        "score": {"total": 86 - index * 3, "manufacturability": 84 - index * 2},
                        "recommended": index == 0,
                    }
                )
            entitlement.ai_jobs_used += 1
            entitlement.version += 1
            db.add(
                EntitlementEvent(
                    entitlement_id=entitlement.id,
                    event_type="AI_JOB_CONSUMED",
                    payload={"jobId": job.id},
                )
            )
            db.commit()
            return {
                "candidates": views,
                "systemRetryUsed": False,
                "entitlement": {
                    "aiJobsUsed": entitlement.ai_jobs_used,
                    "aiJobsTotal": entitlement.ai_jobs_total,
                },
            }

        run_eager_job(db, job, worker, failure_code="AI_GENERATION_FAILED")
    db.refresh(job)
    return to_job_view(job), created


def _base_version_view(version: BaseImageVersion) -> BaseImageVersionView:
    return BaseImageVersionView(
        id=version.id,
        project_id=version.project_id,
        source_asset_id=version.source_asset_id,
        foreground_asset_id=version.foreground_asset_id,
        mask_asset_id=version.mask_asset_id,
        preview_asset={
            "id": version.preview_asset_id,
            "previewUrl": f"/api/v1/assets/{version.preview_asset_id}/content",
        },
        crop=version.crop,
        background_mode=version.background_mode,
        background_palette_color_id=version.background_palette_color_id,
        confirmed_at=version.confirmed_at,
    )


def _apply_crop(image: Image.Image, crop: dict) -> Image.Image:
    width, height = image.size
    left = round(crop["x"] * width)
    top = round(crop["y"] * height)
    right = min(width, round((crop["x"] + crop["width"]) * width))
    bottom = min(height, round((crop["y"] + crop["height"]) * height))
    result = image.crop((left, top, right, bottom))
    if crop.get("flip_x"):
        result = ImageOps.mirror(result)
    if crop.get("flip_y"):
        result = ImageOps.flip(result)
    if crop.get("rotation"):
        result = result.rotate(crop["rotation"], expand=True)
    return result


def _transparent_grid_count(image: Image.Image, width: int, height: int) -> int:
    alpha = image.getchannel("A").resize((width, height), Image.Resampling.BOX)
    return sum(1 for value in alpha.getdata() if value < 128)


def _image_bytes(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
