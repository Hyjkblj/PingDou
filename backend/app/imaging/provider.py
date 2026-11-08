"""Replaceable image providers used by local development and tests."""

import io
from dataclasses import dataclass

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


@dataclass
class RemovalResult:
    foreground_png: bytes
    mask_png: bytes
    white_preview_png: bytes
    width: int
    height: int
    edge_quality_score: int


class LocalImageProvider:
    def remove_background(self, content: bytes, strength: str) -> RemovalResult:
        image = Image.open(io.BytesIO(content)).convert("RGBA")
        width, height = image.size
        pixels = image.load()
        corners = [pixels[0, 0], pixels[width - 1, 0], pixels[0, height - 1], pixels[-1, -1]]
        background = tuple(sum(color[index] for color in corners) // 4 for index in range(3))
        threshold = {"PRESERVE": 24, "STANDARD": 42, "STRONG": 64}[strength]
        mask = Image.new("L", image.size)
        mask_pixels = mask.load()
        for y in range(height):
            for x in range(width):
                red, green, blue, alpha = pixels[x, y]
                distance = abs(red - background[0]) + abs(green - background[1]) + abs(
                    blue - background[2]
                )
                mask_pixels[x, y] = min(alpha, 0 if distance <= threshold else 255)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=0.8))
        foreground = image.copy()
        foreground.putalpha(mask)
        white = Image.new("RGBA", image.size, "white")
        white.alpha_composite(foreground)
        return RemovalResult(
            foreground_png=_png(foreground),
            mask_png=_png(mask),
            white_preview_png=_png(white.convert("RGB")),
            width=width,
            height=height,
            edge_quality_score=88,
        )

    def generate_candidates(self, content: bytes, count: int) -> list[bytes]:
        image = Image.open(io.BytesIO(content)).convert("RGBA")
        alpha = image.getchannel("A")
        rgb = image.convert("RGB")
        candidates: list[bytes] = []
        for index in range(count):
            filtered = rgb.filter(ImageFilter.MedianFilter(size=3))
            filtered = ImageOps.posterize(filtered, 5 if index == 0 else 4)
            filtered = ImageEnhance.Color(filtered).enhance(1.15 + index * 0.1)
            result = filtered.convert("RGBA")
            result.putalpha(alpha)
            candidates.append(_png(result))
        return candidates


def _png(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


image_provider = LocalImageProvider()
