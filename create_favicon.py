#!/usr/bin/env python3

from PIL import Image, ImageDraw, ImageFont
import os

# Create a 32x32 image with transparent background
img = Image.new('RGBA', (32, 32), color=(0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Draw a blue circle as background
draw.ellipse((0, 0, 32, 32), fill=(0, 120, 212, 255))

# Add the letter 'M' in white
try:
    # Try to use a system font
    font = ImageFont.truetype("Arial", 22)
except:
    # Fall back to default font
    font = ImageFont.load_default()

# Draw the letter 'M' centered in the circle
draw.text((8, 4), "M", fill=(255, 255, 255, 255), font=font)

# Save as PNG first
img.save('mini_cursor/static/favicon.png')

# Convert to ICO format
img_ico = img.resize((16, 16))
img.save('mini_cursor/static/favicon.ico', sizes=[(16, 16), (32, 32)])

print("Favicon created successfully!") 