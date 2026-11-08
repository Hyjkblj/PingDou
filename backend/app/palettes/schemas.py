from app.core.schemas import AppSchema


class PaletteView(AppSchema):
    id: str
    brand: str
    series: str
    name: str
    version: str
    status: str
    color_count: int


class PaletteColorView(AppSchema):
    id: str
    code: str
    name: str
    rgb: str
    lab: list[float]
    attributes: list[str]
    enabled: bool

