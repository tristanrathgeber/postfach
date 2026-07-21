"""Erzeugt das Postfach-App-Icon als PNG-Satz: Papierkarte mit Tinte-Kuvert.

Bewusst KEIN Buchstabe — ein klares Kuvert-Mark im „Schreibtisch"-Stil, das
auch bei 16 px als Mail-App lesbar bleibt.

Aufruf (Pillow nur zur Build-Zeit): uv run --with pillow python scripts/make_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "dist" / "icon.iconset"
OUT.mkdir(parents=True, exist_ok=True)

SIZES = [16, 32, 64, 128, 256, 512, 1024]
PAPER, TINTE, HAIRLINE, FLAP = "#FAF9F6", "#2440B3", "#E1DED7", "#E9EDFA"


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = size * 0.06
    # Papierkarte mit weicher Ecke + Haarlinie.
    d.rounded_rectangle([m, m, size - m, size - m], radius=size * 0.22, fill=PAPER,
                        outline=HAIRLINE, width=max(1, size // 200))

    # Kuvert: Körper (Rechteck) + Klappe (V), Tinte-Kontur; Klappe zart gefüllt,
    # damit die Silhouette auch klein als Umschlag liest.
    lw = max(2, int(size * 0.05))
    left, right = size * 0.2, size * 0.8
    top, bottom = size * 0.38, size * 0.64
    apex = size * 0.545  # Spitze der Klappe
    d.polygon([(left, top), (right, top), ((left + right) / 2, apex)], fill=FLAP)
    d.rounded_rectangle([left, top, right, bottom], radius=size * 0.03,
                        outline=TINTE, width=lw)
    d.line([(left, top), ((left + right) / 2, apex), (right, top)], fill=TINTE,
           width=lw, joint="curve")
    return img


for s in SIZES:
    base = draw(s) if s >= 128 else draw(128).resize((s, s), Image.LANCZOS)
    base.save(OUT / f"icon_{s}x{s}.png")
    if s <= 512:
        hi = draw(s * 2) if s * 2 >= 128 else draw(128).resize((s * 2, s * 2), Image.LANCZOS)
        hi.save(OUT / f"icon_{s}x{s}@2x.png")

print(f"Iconset: {OUT}")
