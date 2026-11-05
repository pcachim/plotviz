"""The background of the macOS disk image: assets/background.png (600x400) and assets/background@2x.png.

The two pictures are the same drawing: a very faint, blurred copy of the chart gallery of the
home page of the help (docs/images/ui/home.png), fading away behind the two icons, an arrow from
the application to the Applications folder, and a line of instructions.  The picture does not
carry the version (it is in the name of the .dmg), so it is drawn once and kept in the
repository; run this only to change the look, then commit the two files.

    uv run python util/make_dmg_background.py

create_pkg.sh joins the two into one HiDPI image for Finder (tiffutil) when it builds the .dmg.
The positions of the icons (150,200 and 450,200 on a 600x400 window) are those of create_pkg.sh.
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
HOME = ROOT / "docs" / "images" / "ui" / "home.png"

W, H = 1200, 800                    # the 2x drawing; the 1x file is this one reduced
OPACITY = 0.20                      # how strong the gallery is (0..1)
BLUR = 4                            # in pixels of the 2x drawing
GALLERY_BOX = (456, 174, 1212, 690)   # the 2x3 gallery in home.png, without its dashed frame
ARROW = (136, 144, 158, 255)
CAPTION = "Drag plotviz to the Applications folder"
CAPTION_COLOUR = (96, 102, 114)
FONTS = ["/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Helvetica.ttc",
         "/Library/Fonts/Arial.ttf", "DejaVuSans.ttf"]


def font(size: int):
    for path in FONTS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def gradient(top=(250, 251, 252), bottom=(240, 243, 247)) -> Image.Image:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        draw.line([(0, y), (W, y)], fill=tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img


def band(y: float) -> float:
    """1 at the top and the bottom, 0.35 across the middle where the icons are (y from 0 to 1)."""
    return min(1.0, 0.35 + 1.6 * abs(y - 0.5))


def gallery_layer(background: Image.Image) -> Image.Image:
    """The gallery, scaled to the width, blurred and faint: only its dark parts are drawn, so the
    white of the chart paper leaves no pale panel behind."""
    gallery = Image.open(HOME).convert("RGB").crop(GALLERY_BOX)
    gallery = gallery.resize((W, round(W * gallery.height / gallery.width)), Image.LANCZOS)
    gallery = gallery.filter(ImageFilter.GaussianBlur(BLUR))
    darkness = ImageChops.invert(gallery.convert("L")).point(lambda v: min(255, round(v * 1.6)))
    mask = darkness.point(lambda v: round(v * OPACITY))
    fade = Image.new("L", mask.size)
    fade.putdata([round(255 * band(y / mask.height)) for y in range(mask.height) for _ in range(mask.width)])
    mask = ImageChops.multiply(mask, fade)
    layer = Image.new("RGBA", background.size, (0, 0, 0, 0))
    layer.paste(gallery.convert("RGBA"), ((W - gallery.width) // 2, (H - gallery.height) // 2), mask)
    out = background.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


def add_arrow(img: Image.Image, y=400, x0=470, x1=730, shaft=12, head=54) -> Image.Image:
    """A smooth arrow (drawn four times larger and reduced)."""
    k = 4
    layer = Image.new("RGBA", (W * k, H * k), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    s = shaft * k
    draw.rounded_rectangle((x0 * k, y * k - s // 2, (x1 - head // 2) * k, y * k + s // 2), radius=s // 2, fill=ARROW)
    draw.polygon([((x1 - head) * k, (y - head * 0.62) * k), (x1 * k, y * k), ((x1 - head) * k, (y + head * 0.62) * k)], fill=ARROW)
    out = img.convert("RGBA")
    out.alpha_composite(layer.resize((W, H), Image.LANCZOS))
    return out.convert("RGB")


def add_caption(img: Image.Image, y=708, size=32) -> Image.Image:
    draw = ImageDraw.Draw(img)
    f = font(size)
    draw.text(((W - draw.textlength(CAPTION, font=f)) / 2, y), CAPTION, font=f, fill=CAPTION_COLOUR)
    return img


def main() -> int:
    img = add_caption(add_arrow(gallery_layer(gradient())))
    ASSETS.mkdir(exist_ok=True)
    img.save(ASSETS / "background@2x.png")
    img.resize((W // 2, H // 2), Image.LANCZOS).save(ASSETS / "background.png")
    print(f"wrote {(ASSETS / 'background.png').relative_to(ROOT)} (600x400) and background@2x.png (1200x800)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
