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
clean_image = "clean.jpg"
past_image = "past.jpg"
overlay_image = "overlay.png"

r = requests.get(image_url, timeout=90)
r.raise_for_status()

with open(input_image, "wb") as f:
    f.write(r.content)

img = Image.open(input_image).convert("RGB")

img_ratio = img.width / img.height
target_ratio = W / H

if img_ratio > target_ratio:
    new_h = H
    new_w = int(H * img_ratio)
else:
    new_w = W
    new_h = int(W / img_ratio)

img = img.resize((new_w, new_h), Image.LANCZOS)
left = (new_w - W) // 2
top = (new_h - H) // 2
img = img.crop((left, top, left + W, top + H))

clean = ImageEnhance.Contrast(img).enhance(1.12)
clean = ImageEnhance.Color(clean).enhance(1.18)
clean = ImageEnhance.Sharpness(clean).enhance(1.18)
clean.save(clean_image, quality=95)

past = img.filter(ImageFilter.GaussianBlur(radius=2.2))
past = ImageEnhance.Brightness(past).enhance(0.62)
past = ImageEnhance.Contrast(past).enhance(1.35)
past = ImageEnhance.Color(past).enhance(0.82)
past.save(past_image, quality=95)

overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)

try:
    font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 86)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
except:
    font_big = ImageFont.load_default()
    font_small = ImageFont.load_default()

wrapped = textwrap.wrap(title.upper(), width=17)
wrapped = wrapped[:4]
main_text = "\n".join(wrapped)

tag_text = "À VOIR AVANT/APRÈS"

bbox = draw.multiline_textbbox((0, 0), main_text, font=font_big, spacing=12)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]

box_x1 = 60
box_y1 = int(H * 0.56)
box_x2 = W - 60
box_y2 = box_y1 + th + 135

draw.rounded_rectangle((box_x1 + 8, box_y1 + 8, box_x2 + 8, box_y2 + 8), radius=46, fill=(0, 0, 0, 130))
draw.rounded_rectangle((box_x1, box_y1, box_x2, box_y2), radius=46, fill=(0, 0, 0, 218), outline=(255, 255, 255, 230), width=4)

tag_bbox = draw.textbbox((0, 0), tag_text, font=font_small)
tag_w = tag_bbox[2] - tag_bbox[0]

draw.rounded_rectangle(((W - tag_w) / 2 - 28, box_y1 - 72, (W + tag_w) / 2 + 28, box_y1 - 18), radius=26, fill=(255, 195, 15, 245))
draw.text(((W - tag_w) / 2, box_y1 - 64), tag_text, font=font_small, fill=(0, 0, 0, 255))

draw.multiline_text(((W - tw) / 2 + 4, box_y1 + 64 + 4), main_text, font=font_big, fill=(0, 0, 0, 190), spacing=12, align="center")
draw.multiline_text(((W - tw) / 2, box_y1 + 64), main_text, font=font_big, fill=(255, 255, 255, 255), spacing=12, align="center")

overlay.save(overlay_image)

filter_complex = (
    "[0:v]scale=1080:1920,"
    "zoompan=z='1.28-0.0031*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=90:s=1080x1920:fps=30,"
    "eq=contrast=1.25:saturation=0.85:brightness=-0.08[past];"
    "[1:v]scale=1080:1920,"
    "zoompan=z='1.06+0.0012*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=90:s=1080x1920:fps=30,"
    "eq=contrast=1.10:saturation=1.18[clean];"
    "[past][clean]xfade=transition=fade:duration=0.45:offset=2.42[base];"
    "[2:v]format=rgba,fade=t=in:st=0.35:d=0.25:alpha=1,fade=t=out:st=2.45:d=0.28:alpha=1[txt];"
    "[base][txt]overlay=0:0,"
    "fade=t=in:st=0:d=0.12,fade=t=out:st=2.92:d=0.08"
)

cmd = [
    "ffmpeg", "-y",
    "-loop", "1", "-i", past_image,
    "-loop", "1", "-i", clean_image,
    "-loop", "1", "-i", overlay_image,
    "-filter_complex", filter_complex,
    "-t", "3",
    "-r", "30",
    "-pix_fmt", "yuv420p",
    "-c:v", "libx264",
    "-preset", "medium",
    "-crf", "18",
    "-movflags", "+faststart",
    output_name
]

subprocess.run(cmd, check=True)
