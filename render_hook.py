import sys
import subprocess
import textwrap
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

title = sys.argv[1]
image_url = sys.argv[2]
output_name = sys.argv[3]

W, H = 1080, 1920

input_image = "input.jpg"
base_image = "base.jpg"
past_image = "past.jpg"
impact_image = "impact.jpg"
overlay_image = "overlay.png"

r = requests.get(image_url, timeout=90)
r.raise_for_status()

with open(input_image, "wb") as f:
    f.write(r.content)

img = Image.open(input_image).convert("RGB")

ratio = img.width / img.height
target = W / H

if ratio > target:
    new_h = H
    new_w = int(H * ratio)
else:
    new_w = W
    new_h = int(W / ratio)

img = img.resize((new_w, new_h), Image.LANCZOS)
left = (new_w - W) // 2
top = (new_h - H) // 2
img = img.crop((left, top, left + W, top + H))

base = ImageEnhance.Contrast(img).enhance(1.18)
base = ImageEnhance.Color(base).enhance(1.22)
base = ImageEnhance.Sharpness(base).enhance(1.22)
base.save(base_image, quality=96)

past = img.filter(ImageFilter.GaussianBlur(radius=4))
past = ImageEnhance.Brightness(past).enhance(0.45)
past = ImageEnhance.Contrast(past).enhance(1.55)
past = ImageEnhance.Color(past).enhance(0.65)
past.save(past_image, quality=94)

impact = ImageEnhance.Contrast(img).enhance(1.45)
impact = ImageEnhance.Color(impact).enhance(1.45)
impact = ImageEnhance.Brightness(impact).enhance(1.12)
impact = ImageEnhance.Sharpness(impact).enhance(1.6)
impact.save(impact_image, quality=96)

overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)

try:
    font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 82)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
except:
    font_big = ImageFont.load_default()
    font_small = ImageFont.load_default()

main_text = "\n".join(textwrap.wrap(title.upper(), width=17)[:4])
tag_text = "REGARDE ÇA"

bbox = draw.multiline_textbbox((0, 0), main_text, font=font_big, spacing=10)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]

box_x1 = 55
box_y1 = int(H * 0.57)
box_x2 = W - 55
box_y2 = box_y1 + th + 145

draw.rectangle((0, 0, W, H), fill=(0, 0, 0, 38))

draw.rounded_rectangle(
    (box_x1 + 10, box_y1 + 10, box_x2 + 10, box_y2 + 10),
    radius=48,
    fill=(0, 0, 0, 150)
)

draw.rounded_rectangle(
    (box_x1, box_y1, box_x2, box_y2),
    radius=48,
    fill=(0, 0, 0, 225),
    outline=(255, 255, 255, 235),
    width=4
)

tag_bbox = draw.textbbox((0, 0), tag_text, font=font_small)
tag_w = tag_bbox[2] - tag_bbox[0]

draw.rounded_rectangle(
    ((W - tag_w) / 2 - 34, box_y1 - 78, (W + tag_w) / 2 + 34, box_y1 - 20),
    radius=28,
    fill=(255, 195, 15, 255)
)

draw.text(
    ((W - tag_w) / 2, box_y1 - 69),
    tag_text,
    font=font_small,
    fill=(0, 0, 0, 255)
)

draw.multiline_text(
    ((W - tw) / 2 + 5, box_y1 + 66 + 5),
    main_text,
    font=font_big,
    fill=(0, 0, 0, 210),
    spacing=10,
    align="center"
)

draw.multiline_text(
    ((W - tw) / 2, box_y1 + 66),
    main_text,
    font=font_big,
    fill=(255, 255, 255, 255),
    spacing=10,
    align="center"
)

overlay.save(overlay_image)

filter_complex = (
    "[0:v]scale=1080:1920,"
    "zoompan=z='1.38-0.0042*on':"
    "x='iw/2-(iw/zoom/2)+12*sin(on/2)':"
    "y='ih/2-(ih/zoom/2)+8*cos(on/3)':"
    "d=90:s=1080x1920:fps=30,"
    "eq=contrast=1.35:saturation=0.8:brightness=-0.07,"
    "noise=alls=18:allf=t+u[past];"

    "[1:v]scale=1080:1920,"
    "zoompan=z='1.18-0.0025*on':"
    "x='iw/2-(iw/zoom/2)+8*sin(on/1.5)':"
    "y='ih/2-(ih/zoom/2)+6*cos(on/2)':"
    "d=90:s=1080x1920:fps=30,"
    "eq=contrast=1.25:saturation=1.35:brightness=0.03[impact];"

    "[2:v]scale=1080:1920,"
    "zoompan=z='1.04+0.0008*on':"
    "x='iw/2-(iw/zoom/2)':"
    "y='ih/2-(ih/zoom/2)':"
    "d=90:s=1080x1920:fps=30,"
    "eq=contrast=1.12:saturation=1.22[final];"

    "[past][impact]xfade=transition=pixelize:duration=0.28:offset=0.72[a];"
    "[a][final]xfade=transition=fadeblack:duration=0.42:offset=2.25[base];"

    "[3:v]format=rgba,"
    "fade=t=in:st=0.28:d=0.22:alpha=1,"
    "fade=t=out:st=2.25:d=0.25:alpha=1[txt];"

    "[base][txt]overlay=0:0,"
    "curves=preset=strong_contrast,"
    "fade=t=in:st=0:d=0.08,"
    "fade=t=out:st=2.92:d=0.08"
)

cmd = [
    "ffmpeg", "-y",
    "-loop", "1", "-i", past_image,
    "-loop", "1", "-i", impact_image,
    "-loop", "1", "-i", base_image,
    "-loop", "1", "-i", overlay_image,
    "-filter_complex", filter_complex,
    "-t", "3",
    "-r", "30",
    "-pix_fmt", "yuv420p",
    "-c:v", "libx264",
    "-preset", "medium",
    "-crf", "17",
    "-movflags", "+faststart",
    output_name
]

subprocess.run(cmd, check=True)
