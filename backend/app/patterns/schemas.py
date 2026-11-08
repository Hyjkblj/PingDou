from pydantic import Field

from app.core.schemas import AppSchema


class GridParams(AppSchema):
    width: int = Field(ge=8, le=256)
    height: int = Field(ge=8, le=256)
    bead_size_mm: float = Field(5, gt=0, le=20)


class PatternPaletteParams(AppSchema):
    id: str
    version: str
    disabled_color_ids: list[str] = Field(default_factory=list)


class PatternOptions(AppSchema):
    max_colors: int = Field(24, ge=2, le=64)
    merge_strength: int = Field(30, ge=0, le=100)
    dithering: str = "OFF"
    outline_enhancement: str = "STANDARD"
    small_region_threshold: int = Field(2, ge=0, le=20)
    skin_tone_protection: bool = True
    optimization_target: str = "BALANCED"


class PatternGenerationRequest(AppSchema):
    project_id: str
    base_image_version_id: str
    grid: GridParams
    palette: PatternPaletteParams
    options: PatternOptions = Field(default_factory=PatternOptions)


class CellChange(AppSchema):
    row: int
    column: int
    from_color_id: str | None = None
    to_color_id: str | None = None


class CellPatchRequest(AppSchema):
    pattern_version: int
    operation_id: str
    changes: list[CellChange] = Field(min_length=1, max_length=1000)


class ReplaceColorRequest(AppSchema):
    pattern_version: int
    operation_id: str
    from_color_id: str | None = None
    to_color_id: str | None = None
    respect_locked_cells: bool = True


class CreatePatternVersionRequest(AppSchema):
    pattern_version: int
    name: str
    note: str | None = None
