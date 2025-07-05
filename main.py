import os
import logging
import requests
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
from threading import Thread
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'YOUR_WEBHOOK_URL_HERE')
HUGGING_FACE_API_KEY = os.getenv('HUGGING_FACE_API_KEY', 'YOUR_HUGGING_FACE_API_KEY')

# Flask app
app = Flask(__name__)

# Telegram bot instance
bot = Bot(token=BOT_TOKEN)

class ImageGenerator:
    def __init__(self):
        self.api_url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
        self.headers = {"Authorization": f"Bearer {HUGGING_FACE_API_KEY}"}
    
    def generate_image(self, prompt):
        """Generate image using Hugging Face API"""
        try:
            payload = {
                "inputs": prompt,
                "parameters": {
                    "num_inference_steps": 30,
                    "guidance_scale": 7.5,
                    "width": 512,
                    "height": 512
                }
            }
            
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return None

# Initialize image generator
image_gen = ImageGenerator()

# Bot command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    welcome_message = """
🎨 **Image Generator Bot** 🎨

मैं आपके लिए AI से images बना सकता हूँ!

**कैसे उपयोग करें:**
- बस मुझे कोई भी description भेजें
- मैं उसके लिए image generate करूंगा

**Examples:**
- "एक सुंदर sunset beach पर"
- "a cute cat wearing glasses"
- "futuristic city at night"

**Commands:**
/start - यह message
/help - Help और examples

अब आप मुझे कोई भी prompt भेज सकते हैं! 🚀
    """
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    help_text = """
🔧 **Help & Examples** 🔧

**Good Prompts:**
- "beautiful landscape with mountains"
- "a robot playing guitar"
- "cute puppy in a garden"
- "abstract art with bright colors"

**Tips:**
- English prompts work better
- Be specific about details
- Mention style (realistic, cartoon, etc.)
- Add colors, lighting, mood

**Commands:**
/start - Welcome message
/help - This help message

Just send me any text and I'll create an image! ✨
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def generate_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages and generate images"""
    user_prompt = update.message.text
    user_id = update.effective_user.id
    
    # Send "generating" message
    generating_msg = await update.message.reply_text("🎨 Image generate kar raha hoon... Please wait!")
    
    try:
        # Generate image
        image_data = image_gen.generate_image(user_prompt)
        
        if image_data:
            # Send image
            await update.message.reply_photo(
                photo=image_data,
                caption=f"🎨 **Generated Image**\n\n**Prompt:** {user_prompt}\n\n_Made with ❤️ by AI_",
                parse_mode='Markdown'
            )
            
            # Delete "generating" message
            await generating_msg.delete()
            
            logger.info(f"Image generated for user {user_id}: {user_prompt}")
            
        else:
            await generating_msg.edit_text(
                "❌ Sorry, image generate nahi ho saki. Please try again later or try a different prompt."
            )
            
    except Exception as e:
        logger.error(f"Error in generate_image_handler: {str(e)}")
        await generating_msg.edit_text(
            "❌ Koi error aa gaya hai. Please try again!"
        )

# Create application
application = Application.builder().token(BOT_TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image_handler))

# Flask routes
@app.route('/')
def home():
    return "🤖 Telegram Image Generator Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming updates from Telegram"""
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        # Process update asynchronously
        asyncio.run(application.process_update(update))
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Set webhook for the bot"""
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        success = bot.set_webhook(webhook_url)
        if success:
            return jsonify({"status": "Webhook set successfully", "url": webhook_url})
        else:
            return jsonify({"error": "Failed to set webhook"}), 500
    except Exception as e:
        logger.error(f"Set webhook error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "bot_info": "Image Generator Bot",
        "timestamp": time.time()
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
