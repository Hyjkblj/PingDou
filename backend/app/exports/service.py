import csv
import io
import re
from collections import Counter
from datetime import timedelta

from PIL import Image
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.errors import AppError
from app.core.storage import storage
from app.domain.access import require_entitlement
from app.domain.models import ExportJob, PaletteColor, Pattern, PatternSnapshot, Project
from app.patterns.engine import render_preview

from .schemas import ExportRequest, ExportView

FORMATS = {"PNG", "PDF", "CSV"}
MIME_TYPES = {"PNG": "image/png", "PDF": "application/pdf", "CSV": "text/csv"}


def create_export(
    db: Session,
    user_id: str,
    body: ExportRequest,
    idempotency_key: str,
) -> tuple[ExportView, bool]:
    pattern = db.query(Pattern).filter(Pattern.id == body.pattern_id).first()
    if not pattern:
        raise AppError("PATTERN_NOT_FOUND", "图纸不存在", status_code=404)
    entitlement = require_entitlement(
        db, user_id, pattern.project_id, require_download_window=True
    )
    export_format = body.format.upper()
    if export_format not in FORMATS:
        raise AppError("EXPORT_FORMAT_UNSUPPORTED", "不支持该导出格式", status_code=400)
    existing = db.query(ExportJob).filter(
        ExportJob.pattern_id == pattern.id,
        ExportJob.pattern_version == body.pattern_version,
        ExportJob.idempotency_key == idempotency_key,
    ).first()
    if existing:
        return export_view(existing), False
    matrix = _matrix_for_version(db, pattern, body.pattern_version)
    project = db.query(Project).filter(Project.id == pattern.project_id).first()
    export = ExportJob(
        project_id=pattern.project_id,
        user_id=user_id,
        pattern_id=pattern.id,
        pattern_version=body.pattern_version,
        format=export_format,
        options=body.options,
        status="RUNNING",
        idempotency_key=idempotency_key,
        retained_until=entitlement.download_expires_at or utcnow() + timedelta(days=30),
    )
    db.add(export)
    db.commit()
    db.refresh(export)
    try:
        colors = db.query(PaletteColor).filter(
            PaletteColor.palette_id == pattern.palette_id
        ).order_by(PaletteColor.sort_order).all()
        content, page_count = _render_export(export_format, pattern, matrix, colors, body.options)
        base_name = re.sub(r"[^A-Za-z0-9_-]", "_", project.name if project else "pingdou")
        file_name = f"{base_name or 'pingdou'}-v{body.pattern_version}.{export_format.lower()}"
        storage_key = (
            f"users/{user_id}/projects/{pattern.project_id}/exports/{export.id}."
            f"{export_format.lower()}"
        )
        storage.write(storage_key, content)
        export.storage_key = storage_key
        export.file_name = file_name
        export.file_size = len(content)
        export.page_count = page_count
        export.status = "SUCCEEDED"
        db.commit()
        db.refresh(export)
        return export_view(export), True
    except Exception as exc:
        db.rollback()
        current = db.query(ExportJob).filter(ExportJob.id == export.id).first()
        if current:
            current.status = "FAILED"
            current.error_code = "EXPORT_FAILED"
            current.error_message = str(exc)
            db.commit()
        raise AppError("EXPORT_FAILED", "导出失败", status_code=500, retryable=True) from exc


def get_export(db: Session, user_id: str, export_id: str) -> ExportView:
    export = _require_export(db, user_id, export_id)
    return export_view(export)


def get_export_file(db: Session, user_id: str, export_id: str) -> tuple[ExportJob, str]:
    export = _require_export(db, user_id, export_id)
    require_entitlement(db, user_id, export.project_id, require_download_window=True)
    if export.status != "SUCCEEDED" or not export.storage_key:
        raise AppError("EXPORT_FAILED", "导出文件不可用", status_code=409)
    return export, MIME_TYPES[export.format]


def export_view(export: ExportJob) -> ExportView:
    downloadable = export.status == "SUCCEEDED" and bool(export.storage_key)
    expires_at = utcnow() + timedelta(minutes=15) if downloadable else None
    error = None
    if export.status == "FAILED":
        error = {"code": export.error_code, "message": export.error_message, "retryable": True}
    return ExportView(
        export_id=export.id,
        status=export.status,
        format=export.format,
        file_name=export.file_name,
        file_size=export.file_size,
        page_count=export.page_count,
        download_url=f"/api/v1/export-jobs/{export.id}/download" if downloadable else None,
        download_url_expires_at=expires_at,
        retained_until=export.retained_until,
        error=error,
    )


def _matrix_for_version(db: Session, pattern: Pattern, version: int) -> list:
    if version == pattern.version:
        return pattern.matrix
    snapshot = db.query(PatternSnapshot).filter(
        PatternSnapshot.pattern_id == pattern.id,
        PatternSnapshot.pattern_version == version,
    ).order_by(PatternSnapshot.created_at.desc()).first()
    if not snapshot:
        raise AppError("PATTERN_VERSION_NOT_FOUND", "图纸版本不存在", status_code=404)
    return snapshot.matrix


def _render_export(
    export_format: str,
    pattern: Pattern,
    matrix: list,
    colors: list[PaletteColor],
    options: dict,
) -> tuple[bytes, int]:
    if export_format == "PNG":
        return render_preview(matrix, colors, scale=16), 1
    if export_format == "CSV":
        return _render_csv(matrix, colors, options), 1
    return _render_pdf(pattern, matrix, colors, options), 1


def _render_csv(matrix: list, colors: list[PaletteColor], options: dict) -> bytes:
    code_by_id = {color.id: color.code for color in colors}
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerows([[code_by_id.get(cell, "") if cell else "" for cell in row] for row in matrix])
    if options.get("includeMaterialList", True):
        writer.writerow([])
        writer.writerow(["color_code", "net_count", "recommended_count"])
        counts = Counter(cell for row in matrix for cell in row if cell)
        waste_rate = float(options.get("wasteRate", 0.05))
        for color in colors:
            if color.id in counts:
                count = counts[color.id]
                writer.writerow([color.code, count, int(count * (1 + waste_rate) + 0.9999)])
    return output.getvalue().encode("utf-8-sig")


def _render_pdf(
    pattern: Pattern, matrix: list, colors: list[PaletteColor], options: dict
) -> bytes:
    output = io.BytesIO()
    page_size = A3 if options.get("paperSize") == "A3" else A4
    if options.get("orientation") == "LANDSCAPE":
        page_size = landscape(page_size)
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    document = canvas.Canvas(output, pagesize=page_size)
    page_width, page_height = page_size
    document.setFont("STSong-Light", 14)
    document.drawString(36, page_height - 36, f"拼豆图纸 v{pattern.version}")
    preview = render_preview(matrix, colors, scale=10)
    image = Image.open(io.BytesIO(preview))
    max_width = page_width - 72
    max_height = page_height - 150
    scale = min(max_width / image.width, max_height / image.height)
    draw_width = image.width * scale
    draw_height = image.height * scale
    document.drawImage(
        ImageReader(io.BytesIO(preview)),
        36,
        page_height - 60 - draw_height,
        width=draw_width,
        height=draw_height,
    )
    document.setFont("STSong-Light", 9)
    document.drawString(
        36,
        36,
        f"网格 {pattern.width} x {pattern.height} | 色板 {pattern.palette_version}",
    )
    document.showPage()
    document.save()
    return output.getvalue()


def _require_export(db: Session, user_id: str, export_id: str) -> ExportJob:
    export = db.query(ExportJob).filter(
        ExportJob.id == export_id,
        ExportJob.user_id == user_id,
    ).first()
    if not export:
        raise AppError("EXPORT_NOT_FOUND", "导出任务不存在", status_code=404)
    return export
