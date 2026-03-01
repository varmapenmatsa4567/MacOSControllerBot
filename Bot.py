from telegram import Update, InputMediaPhoto
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from utils import runShortCut, ReplyBody, getScreenshot, removeFinderItem, getScreenshotWithGrid
import pyautogui
import time
import io
import hashlib

class Bot:
    def __init__(self, botToken, admin):
        self.botToken = botToken
        self.admin = admin
        self.zone_store = {}
        self.live_mode = False
        self.live_message = None
        self.last_frame_hash = None
        self.bot = ApplicationBuilder().token(botToken).build()
        self.bot.add_handler(CommandHandler("start", self.handle_start))
        self.bot.add_handler(CommandHandler("screenshot", self.handle_screenshot))
        self.bot.add_handler(CommandHandler("control", self.handle_control))
        self.bot.add_handler(CommandHandler("click", self.handle_click))
        self.bot.add_handler(CommandHandler("debug", self.debug))
        self.bot.add_handler(CommandHandler("scroll", self.handle_scroll))
        self.bot.add_handler(CommandHandler("type", self.handle_type_text))
        self.bot.add_handler(CommandHandler("press", self.handle_press_key))
        self.bot.add_handler(CommandHandler("livemode", self.handle_live))
        self.bot.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, self.handle_text))

    # Send 
    async def sendReply(self, update: Update, replyBody: ReplyBody):
        if replyBody.text:
            return await update.message.reply_text(replyBody.text)
        if replyBody.photo:
            return await update.message.reply_photo(replyBody.photo, replyBody.caption)

    # Check whether user is admin or not
    def isAdmin(self, update: Update):
        return update.effective_user.id == self.admin

    # Handling any text or any multi media other than Commands
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Only admin is allowed to control the system
        if not self.isAdmin:
            return
        
        await update.message.chat.send_action(ChatAction.TYPING)

        message = update.message

        userText = None
        photoFileId = None

        # If user sends the photo
        if message.photo:
            # Get photo id
            photo = message.photo[-1]
            photoFileId = photo.file_id

            # If user types text along with image -> It is in caption
            userText = message.caption
        
        # If user send only text
        elif message.text:
            userText = message.text

        # Getting the file using File ID
        file = None
        if photoFileId:
            file = await context.bot.get_file(photoFileId)

        runShortCut(userText)

        replyBody = ReplyBody()
        replyBody.setText("Done")

        await self.sendReply(update, replyBody)

    # Send screenshot
    async def handle_screenshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
        screenshot = getScreenshot()
        replyBody = ReplyBody()
        replyBody.photo = screenshot
        await self.sendReply(update, replyBody)
    
    # Sends screenshot with grid overlay -> user can provide where to click
    async def handle_control(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
        img_bytes, zones = getScreenshotWithGrid()
        self.zone_store["zones"] = zones
        await update.message.reply_photo(
            photo=img_bytes,
            caption="📸 Reply with a zone label to click it.\nExample: `B3`",
            parse_mode="Markdown"
        )

    # Presses specified Key / Hotkey
    async def handle_press_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Usage: /press {key}")
            return
    
        text = " ".join(context.args)
        if "+" in text and len(text) > 1:
            pyautogui.hotkey(*text.split("+"))
        else:
            pyautogui.press(text)

        await update.message.reply_text(f"✅ Pressed: `{text}`", parse_mode="Markdown")

    # Types whatever user sends and then press enter
    async def handle_type_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Usage: /type hello world")
            return
        
        text = " ".join(context.args)
        pyautogui.typewrite(text, interval=0.05)
        pyautogui.press("enter")
        await update.message.reply_text(f"✅ Typed: `{text}`", parse_mode="Markdown")

    # Clicks on the center of the user provided grid
    async def handle_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        label = update.message.text.strip().upper().split(" ")[1]
        zones = self.zone_store.get("zones", {})
        
        if label in zones:
            x, y = zones[label]
            pyautogui.click(x, y)
            await update.message.reply_text(f"✅ Clicked zone {label} → ({x}, {y})")
            time.sleep(3)
            await self.handle_control(update, context)
        else:
            await update.message.reply_text(f"❓ Unknown zone `{label}`. Try A1–D6.", parse_mode="Markdown")

    # Scroll the system by specified parameters
    async def handle_scroll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.isAdmin:
            return

        try:
            direction = context.args[0].lower()  # up / down / left / right
            amount = int(context.args[1]) if len(context.args) > 1 else 3  # default 3 clicks
        except (IndexError, ValueError):
            await update.message.reply_text(
                "Usage: /scroll <direction> [amount]\n"
                "Examples:\n"
                "  /scroll down 5\n"
                "  /scroll up 3\n"
                "  /scroll left 2\n"
                "  /scroll right 2"
            )
            return

        if direction == "down":
            pyautogui.scroll(-amount)
        elif direction == "up":
            pyautogui.scroll(amount)
        elif direction == "left":
            pyautogui.hscroll(-amount)
        elif direction == "right":
            pyautogui.hscroll(amount)
        else:
            await update.message.reply_text("❌ Direction must be: up, down, left, right")
            return

        await update.message.reply_text(f"✅ Scrolled {direction} by {amount}")
        time.sleep(1)
        await self.handle_control(update, context)
        
    async def debug(self, update: Update, contex: ContextTypes.DEFAULT_TYPE):
        screen_w, screen_h = pyautogui.size()
        img = pyautogui.screenshot()
        img_w, img_h = img.size
        await update.message.reply_text(
            f"Logical (pyautogui): {screen_w}×{screen_h}\n"
            f"Pixel (screenshot):  {img_w}×{img_h}\n"
            f"Scale factor: {img_w/screen_w}×{img_h/screen_h}"
        )

    async def handle_live(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print("Handling live")
        if not context.args:
            await update.message.reply_text("Usage: /livemode on | off")
            return

        command = context.args[0].lower()
        # print(command)

        if command == "on":
            if self.live_mode:
                await update.message.reply_text("Already streaming.")
                return

            self.live_mode = True
            msg = await update.message.reply_text("🔴 Live mode started...")
            self.live_message = msg

            context.application.create_task(self.stream_screen(context))

        elif command == "off":
            self.live_mode = False
            await update.message.reply_text("🛑 Live mode stopped.")

    async def stream_screen(self, context: ContextTypes.DEFAULT_TYPE):
        while self.live_mode:
            screenshot = pyautogui.screenshot().convert("RGB")
            # Resize for speed (important!)
            screenshot = screenshot.resize((800, 450))

            bio = io.BytesIO()
            bio.name = "live.jpg"
            screenshot.save(bio, "JPEG", quality=60)

            frame_bytes = bio.getvalue()

            # Create hash of image
            current_hash = hashlib.md5(frame_bytes).hexdigest()

            if current_hash != self.last_frame_hash:
                bio.seek(0)
                try:
                    await context.bot.edit_message_media(
                        chat_id=self.live_message.chat_id,
                        message_id=self.live_message.message_id,
                        media=InputMediaPhoto(bio)
                    )
                    self.last_frame_hash = current_hash
                except Exception as e:
                    print("Edit failed:", e)
        
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        replyBody = ReplyBody()
        replyBody.setText("Hey, I'm Alive")
        await self.sendReply(update, replyBody)

    def run(self):
        print("Bot Started...")
        self.bot.run_polling()


if __name__ == "__main__":
    bot = Bot("YOUR_TOKEN")
    bot.run()