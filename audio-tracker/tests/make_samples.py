"""Creates fictional Marketplace-style test screenshots (1080 x 2400) in tests/samples/.

These are made-up test images only - no real listing, seller or Facebook content.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageEnhance

OUT = Path(__file__).resolve().parent / "samples"

FONT_CANDIDATES = {
    "regular": ["/usr/share/fonts/opentype/inter/Inter-Regular.otf", "C:/Windows/Fonts/segoeui.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "bold": ["/usr/share/fonts/opentype/inter/Inter-Bold.otf", "C:/Windows/Fonts/segoeuib.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
}


def font(kind, size):
    for p in FONT_CANDIDATES[kind]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def speaker_photo(size=1080, shade=0):
    """A drawn 'photo' of a pair of full-range drivers on a wooden table."""
    im = Image.new("RGB", (size, size), (120 + shade, 96 + shade, 70 + shade))
    d = ImageDraw.Draw(im)
    for y in range(0, size, 36):
        d.line([(0, y), (size, y + 18)], fill=(105 + shade, 82 + shade, 58 + shade), width=4)
    for cx in (300, 780):
        cy = 560
        d.rectangle([cx - 210, cy - 210, cx + 210, cy + 210], fill=(40, 40, 42))
        d.ellipse([cx - 190, cy - 190, cx + 190, cy + 190], fill=(25, 25, 25))
        d.ellipse([cx - 165, cy - 165, cx + 165, cy + 165], fill=(150, 140, 120))
        d.ellipse([cx - 60, cy - 60, cx + 60, cy + 60], fill=(60, 55, 50))
        for a in (-1, 1):
            for b in (-1, 1):
                d.ellipse([cx + a * 185 - 12, cy + b * 185 - 12, cx + a * 185 + 12, cy + b * 185 + 12],
                          fill=(170, 170, 170))
    return im


def amp_photo(size=1080):
    """A drawn 'photo' of a small green amplifier board with heatsink and capacitors."""
    im = Image.new("RGB", (size, size), (200, 200, 205))
    d = ImageDraw.Draw(im)
    d.rectangle([140, 260, 940, 820], fill=(20, 110, 60))
    d.rectangle([420, 300, 700, 520], fill=(160, 160, 170))
    for x in range(430, 700, 22):
        d.rectangle([x, 300, x + 10, 520], fill=(120, 120, 130))
    for i, x in enumerate((200, 300, 780, 860)):
        d.ellipse([x - 45, 600, x + 45, 690], fill=(30, 30, 90))
        d.rectangle([x - 45, 645, x + 45, 760], fill=(30, 30, 90))
    d.rectangle([160, 380, 260, 470], fill=(20, 140, 220))
    d.rectangle([820, 380, 920, 470], fill=(20, 140, 220))
    d.ellipse([500, 620, 600, 720], fill=(15, 15, 15))
    return im


def wrap(draw, text, fnt, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def screenshot(path, *, photo, title, price, old_price=None, listed, condition, description, seller,
               joined, clock="08:30", scroll=0):
    W, H = 1080, 2400
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    grey, dark = (101, 103, 107), (5, 5, 5)

    y_photo = 170 - scroll
    im.paste(photo, (0, y_photo))
    # status bar + top bar (drawn after the photo so they stay on top when scrolled)
    d.rectangle([0, 0, W, 160], fill="white")
    d.text((40, 22), clock, font=font("bold", 36), fill=dark)
    d.text((W - 200, 22), "4G  76%", font=font("regular", 34), fill=dark)
    d.line([(50, 115), (80, 90)], fill=dark, width=6)
    d.line([(50, 115), (80, 140)], fill=dark, width=6)
    d.ellipse([W - 100, 92, W - 60, 132], outline=dark, width=5)

    for i in range(4):
        d.ellipse([480 + i * 36, y_photo + 1100, 496 + i * 36, y_photo + 1116],
                  fill=(28, 30, 33) if i == 0 else (200, 200, 200))

    y = y_photo + 1150
    f_title, f_price = font("bold", 50), font("bold", 46)
    for line in wrap(d, title, f_title, W - 90):
        d.text((40, y), line, font=f_title, fill=dark)
        y += 64
    y += 6
    d.text((40, y), price, font=f_price, fill=dark)
    if old_price:
        x = 40 + d.textlength(price, font=f_price) + 24
        f_old = font("regular", 38)
        d.text((x, y + 6), old_price, font=f_old, fill=grey)
        tw = d.textlength(old_price, font=f_old)
        d.line([(x, y + 30), (x + tw, y + 30)], fill=grey, width=3)
    y += 70
    d.text((40, y), listed, font=font("regular", 36), fill=grey)
    y += 80

    for i, label in enumerate(("Message", "Save", "Share")):
        x0 = 40 + i * 340
        d.rounded_rectangle([x0, y, x0 + 310, y + 90], radius=16, fill=(228, 230, 235))
        d.text((x0 + 155 - d.textlength(label, font=font("bold", 34)) / 2, y + 24), label,
               font=font("bold", 34), fill=dark)
    y += 120
    d.rounded_rectangle([40, y, W - 40, y + 170], radius=20, fill=(240, 242, 245))
    d.text((70, y + 20), "Send seller a message", font=font("bold", 34), fill=dark)
    d.rounded_rectangle([70, y + 80, W - 240, y + 160], radius=40, fill="white")
    d.text((100, y + 98), "Hi, is this available?", font=font("regular", 34), fill=grey)
    d.text((W - 200, y + 98), "Send", font=font("bold", 34), fill=(8, 102, 255))
    y += 200

    d.text((40, y), "Details", font=font("bold", 42), fill=dark)
    y += 60
    d.text((40, y), "Condition", font=font("regular", 36), fill=grey)
    d.text((420, y), condition, font=font("regular", 36), fill=dark)
    y += 70
    d.text((40, y), "Description", font=font("bold", 38), fill=dark)
    y += 55
    for line in wrap(d, description, font("regular", 36), W - 80):
        d.text((40, y), line, font=font("regular", 36), fill=dark)
        y += 50
    y += 30
    d.line([(40, y), (W - 40, y)], fill=(220, 220, 220), width=2)
    y += 30
    d.text((40, y), "Seller information", font=font("bold", 40), fill=dark)
    d.text((W - 240, y + 4), "See profile", font=font("regular", 34), fill=(8, 102, 255))
    y += 70
    d.ellipse([40, y, 140, y + 100], fill=(170, 180, 200))
    d.text((170, y + 8), seller, font=font("bold", 38), fill=dark)
    d.text((170, y + 58), joined, font=font("regular", 32), fill=grey)
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / path, "JPEG", quality=88)
    return OUT / path


def main():
    speakers = speaker_photo()
    amp = amp_photo()
    made = [
        screenshot("Screenshot_20261105-191500_Facebook.jpg", photo=speakers,
                   title="Tang Band 4 inch full range speaker pair", price="₹1,250",
                   listed="Listed 2 days ago in Kochi, KL", condition="Used - good",
                   description="Pair of 4 inch full range drivers, 8 ohm. Both working, no rub. "
                               "Removed from a bookshelf build. Pickup only.",
                   seller="Arun Mathew", joined="Joined Facebook in 2014", clock="19:15"),
        # same listing a week later: lower price, old price struck through, scrolled a little
        screenshot("Screenshot_20261112-083000_Facebook.jpg", photo=speakers,
                   title="Tang Band 4 inch full range speaker pair", price="₹950", old_price="₹1,250",
                   listed="Listed 1 week ago in Kochi, KL", condition="Used - good",
                   description="Pair of 4 inch full range drivers, 8 ohm. Both working, no rub. "
                               "Removed from a bookshelf build. Pickup only.",
                   seller="Arun Mathew", joined="Joined Facebook in 2014", clock="08:30", scroll=40),
        screenshot("Screenshot_20261110-210500_Facebook.jpg", photo=amp,
                   title="TPA3116D2 2x50W amplifier board with Bluetooth", price="₹650",
                   listed="Listed 5 hours ago in Aluva, KL", condition="Used - like new",
                   description="TPA3116 class D stereo board. Needs 12-24V supply. Tested OK.",
                   seller="Nikhil Raj", joined="Joined Facebook in 2017", clock="21:05"),
        # similar photo, different wording and seller -> should go to "Possible duplicate"
        screenshot("Screenshot_20261111-120000_Facebook.jpg",
                   photo=ImageEnhance.Brightness(amp.crop((60, 60, 1020, 1020)).resize((1080, 1080))).enhance(1.08),
                   title="Bluetooth amp board TPA3116 50 watt x 2", price="₹600",
                   listed="Listed 1 day ago in Aluva, KL", condition="Used - good",
                   description="Class D Bluetooth amplifier. Selling as I upgraded.",
                   seller="Nikhil R", joined="Joined Facebook in 2017", clock="12:00", scroll=20),
    ]
    for p in made:
        print("created", p)


if __name__ == "__main__":
    sys.exit(main())
