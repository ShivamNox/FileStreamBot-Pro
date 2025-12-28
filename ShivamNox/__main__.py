import os
import sys
import asyncio
import logging
import signal

# Suppress warnings FIRST
logging.getLogger("asyncio").setLevel(logging.ERROR)

from pyrogram import idle
from aiohttp import web
from ShivamNox.bot import StreamBot
from ShivamNox.vars import Var
from ShivamNox.server import web_server
from ShivamNox.utils.keepalive import ping_server
from ShivamNox.bot.clients import initialize_clients
from pyrogram.errors import BadMsgNotification
from pyrogram.types import BotCommand

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Prevent early termination
startup_complete = False

def signal_handler(sig, frame):
    if not startup_complete:
        logger.warning(f"Ignoring signal {sig} during startup")
        return
    logger.info("Shutting down...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


async def set_bot_commands():
    commands = [
        BotCommand("start", "🚀 Launch the bot"),
        BotCommand("ping", "📶 Check responsiveness"),
        BotCommand("about", "ℹ️ About this bot"),
        BotCommand("status", "📊 Bot status"),
    ]
    try:
        await StreamBot.set_bot_commands(commands)
    except Exception as e:
        logger.warning(f"Failed to set commands: {e}")


async def start_services():
    global startup_complete
    
    logger.info("Starting FileStreamBot...")
    
    # Start bot
    for attempt in range(5):
        try:
            await StreamBot.start()
            break
        except BadMsgNotification as e:
            logger.warning(f"Retry {attempt + 1}/5: {e}")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error: {e}")
            await asyncio.sleep(3)
    else:
        logger.error("Failed to start bot after 5 attempts")
        sys.exit(1)
    
    logger.info(f"Bot started as @{StreamBot.username}")
    
    # Initialize clients
    await initialize_clients()
    
    # Set commands
    await set_bot_commands()
    
    # Start web server
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, Var.PORT).start()
    logger.info(f"Web server started on {bind_address}:{Var.PORT}")
    
    # Start keep-alive
    if Var.ON_HEROKU:
        await asyncio.sleep(5)
        asyncio.create_task(ping_server())
    
    # Mark startup complete
    startup_complete = True
    
    logger.info("=" * 50)
    logger.info(f"✅ Bot: @{StreamBot.username}")
    logger.info(f"✅ Server: http://{bind_address}:{Var.PORT}")
    logger.info(f"✅ Owner: {Var.OWNER_USERNAME}")
    logger.info("=" * 50)
    logger.info("🎉 Bot is ready and listening for messages!")
    
    await idle()


if __name__ == '__main__':
    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        logger.info('Stopped by user')
