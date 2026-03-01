import subprocess
import uuid
import os
from PIL import Image, ImageDraw, ImageFont
import io, pyautogui

COLS, ROWS = 60, 45  # creates a 6×4 = 24 zone grid

# Object to denote Multiple Types of Content
class ReplyBody:
    def __init__(self):
        self.text = None
        self.photo = None
        self.caption = None

    def setText(self, text):
        self.text = text
    
    def setPhoto(self, photo):
        self.photo = photo
    
    def setCaption(self, caption):
        self.caption = caption

# Run User Created shortcut
def runShortCut(userCommand):
    subprocess.run(
        f'shortcuts run "Controller" <<< "{userCommand}"',
        shell=True,
        executable="/bin/bash"
    )

# Take screenshot and return file path
def getScreenshot():
    img = pyautogui.screenshot()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def getScreenshotWithGrid():
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size=24)
    except:
        font = ImageFont.load_default()  # fallback

    img = pyautogui.screenshot()
    screen_w, screen_h = pyautogui.size()  # logical size (what pyautogui uses)
    img_w, img_h = img.size                # actual pixel size (2x on Retina)
    
    # Scale factor (usually 2.0 on Retina Macs)
    scale_x = img_w / screen_w
    scale_y = img_h / screen_h

    draw = ImageDraw.Draw(img)
    cell_w = img_w // COLS
    cell_h = img_h // ROWS
    zones = {}

    for row in range(ROWS):
        for col in range(COLS):
            label = f"{chr(65+row)}{col+1}"
            x1, y1 = col * cell_w, row * cell_h
            x2, y2 = x1 + cell_w, y1 + cell_h

            # Divide by scale to get logical coords for pyautogui
            cx = int(((x1 + x2) // 2) / scale_x)
            cy = int(((y1 + y2) // 2) / scale_y)
            zones[label] = (cx, cy)

            draw.rectangle([x1, y1, x2, y2], outline="red", width=1)
            draw.text((x1 + 5, y1 + 5), label, fill="red", font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), zones

# Remove File / Folder
def removeFinderItem(path):
    os.remove(path)