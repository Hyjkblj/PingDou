from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.domain.models import Palette, PaletteColor

from .schemas import PaletteColorView, PaletteView

DEFAULT_COLORS = [
    ("H01", "纯白", "#FFFFFF", [100.0, 0.0, 0.0]),
    ("H02", "象牙白", "#F4F0E6", [94.2, 0.8, 5.3]),
    ("H03", "浅肤色", "#F3C6A5", [82.0, 14.0, 22.0]),
    ("H04", "肤色", "#D99A72", [69.0, 20.0, 29.0]),
    ("H05", "棕色", "#7A4A2E", [36.0, 18.0, 25.0]),
    ("H06", "黑色", "#1C1C1C", [10.0, 0.0, 0.0]),
    ("H07", "灰色", "#8B9095", [59.0, -1.0, -3.0]),
    ("H08", "红色", "#D83A3A", [49.0, 61.0, 39.0]),
    ("H09", "粉色", "#F48FB1", [72.0, 43.0, 2.0]),
    ("H10", "黄色", "#F4D44D", [86.0, -2.0, 69.0]),
    ("H11", "绿色", "#4A9B62", [57.0, -37.0, 23.0]),
    ("H12", "浅蓝", "#75B9E7", [72.0, -12.0, -30.0]),
    ("H13", "蓝色", "#3568B8", [45.0, 9.0, -48.0]),
    ("H14", "紫色", "#8064A2", [47.0, 20.0, -30.0]),
    ("H15", "橙色", "#EB7F34", [66.0, 38.0, 56.0]),
    ("H16", "深绿", "#24563A", [31.0, -25.0, 13.0]),
]


def ensure_default_palette(db: Session) -> Palette:
    palette = db.query(Palette).filter(Palette.version == "PINGDOU-2026.1").first()
    if palette:
        return palette
    palette = Palette(
        brand="PingDou",
        series="MVP",
        name="PingDou 基础色板",
        version="PINGDOU-2026.1",
        status="ACTIVE",
    )
    db.add(palette)
    db.flush()
    for index, (code, name, rgb, lab) in enumerate(DEFAULT_COLORS):
        db.add(
            PaletteColor(
                palette_id=palette.id,
                code=code,
                name=name,
                rgb=rgb,
                lab=lab,
                attributes=["OPAQUE"],
                enabled=True,
                sort_order=index,
            )
        )
    db.commit()
    db.refresh(palette)
    return palette


def list_palettes(db: Session, brand: str | None, status: str | None) -> list[PaletteView]:
    ensure_default_palette(db)
    query = db.query(Palette)
    if brand:
        query = query.filter(Palette.brand == brand)
    if status:
        query = query.filter(Palette.status == status)
    palettes = query.order_by(Palette.brand, Palette.series, Palette.version).all()
    return [
        PaletteView(
            id=palette.id,
            brand=palette.brand,
            series=palette.series,
            name=palette.name,
            version=palette.version,
            status=palette.status,
            color_count=db.query(PaletteColor).filter(
                PaletteColor.palette_id == palette.id,
                PaletteColor.enabled.is_(True),
            ).count(),
        )
        for palette in palettes
    ]


def list_colors(db: Session, palette_id: str, version: str | None) -> list[PaletteColorView]:
    ensure_default_palette(db)
    filters = [Palette.id == palette_id]
    if version:
        filters.append(Palette.version == version)
    palette = db.query(Palette).filter(*filters).first()
    if not palette:
        raise AppError("PALETTE_VERSION_NOT_FOUND", "色板版本不存在", status_code=404)
    colors = db.query(PaletteColor).filter(
        PaletteColor.palette_id == palette.id
    ).order_by(PaletteColor.sort_order).all()
    return [
        PaletteColorView(
            id=color.id,
            code=color.code,
            name=color.name,
            rgb=color.rgb,
            lab=color.lab,
            attributes=color.attributes,
            enabled=color.enabled,
        )
        for color in colors
    ]

