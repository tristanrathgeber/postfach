"""Erzeugt das Postfach-App-Icon (P auf Papier, Tinte-Akzent) als PNG-Satz.

Aufruf (Pillow nur zur Build-Zeit): uv run --with pillow python scripts/make_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "dist" / "icon.iconset"
OUT.mkdir(parents=True, exist_ok=True)

SIZES = [16, 32, 64, 128, 256, 512, 1024]
PAPER, INK, TINTE, HAIRLINE = "#FAF9F6", "#1A1917", "#2440B3", "#E8E5DF"


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin = size * 0.06
    radius = size * 0.22
    d.rounded_rectangle([margin, margin, size - margin, size - margin], radius=radius, fill=PAPER, outline=HAIRLINE, width=max(1, size // 256))
    # Kuvert-Andeutung: Tinte-Linie als Umschlagklappe
    d.line([(size * 0.2, size * 0.34), (size * 0.5, size * 0.56), (size * 0.8, size * 0.34)], fill=TINTE, width=max(2, int(size * 0.045)))
    # Serifen-P
    font = None
    for candidate in ["/System/Library/Fonts/Supplemental/Georgia Italic.ttf", "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf"]:
        try:
            font = ImageFont.truetype(candidate, int(size * 0.5))
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    d.text((size * 0.5, size * 0.62), "P", font=font, fill=INK, anchor="mm")
    return img


for s in SIZES:
    img = draw(s if s >= 64 else 64).resize((s, s), Image.LANCZOS) if s < 64 else draw(s)
    img.save(OUT / f"icon_{s}x{s}.png")
    if s <= 512:
        draw(s * 2).save(OUT / f"icon_{s}x{s}@2x.png")

print(f"Iconset: {OUT}")
