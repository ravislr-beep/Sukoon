"""Combine the five zero-downtime schema images from the Pega Helm charts into one numbered strip."""
from PIL import Image, ImageDraw, ImageFont

STEPS = [
    ("create-blank-schema", "1  Create new schemas"),
    ("migrate-rule-rnew-dtemp-schemas", "2  Migrate rules"),
    ("upgrade-rules-rnew-schema", "3  Upgrade rules"),
    ("upgrade-rules-dtmp-schema", "4  Upgrade data"),
    ("updated-schemas", "5  Final state"),
]
SCALE = 2
PANEL_H = 562 * SCALE
GAP = 30
LABEL_H = 90
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def main():
    imgs = []
    for name, label in STEPS:
        im = Image.open(f"img/public/{name}.png").convert("RGBA")
        im = im.resize((im.width * SCALE, im.height * SCALE), Image.LANCZOS)
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[3])
        imgs.append((bg, label))
    width = sum(i.width for i, _ in imgs) + GAP * (len(imgs) + 1)
    height = PANEL_H + LABEL_H + GAP * 2
    out = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(out)
    font = ImageFont.truetype(FONT, 30)
    x = GAP
    for im, label in imgs:
        y = GAP + LABEL_H + (PANEL_H - im.height) // 2
        out.paste(im, (x, y))
        tw = d.textbbox((0, 0), label, font=font)[2]
        d.rounded_rectangle([x, GAP, x + im.width, GAP + LABEL_H - 20], radius=12, fill=(31, 56, 100))
        d.text((x + (im.width - tw) // 2, GAP + 14), label, font=font, fill="white")
        x += im.width + GAP
    out.save("img/generated/fig_zdt_schemas.png", dpi=(200, 200))


if __name__ == "__main__":
    main()
