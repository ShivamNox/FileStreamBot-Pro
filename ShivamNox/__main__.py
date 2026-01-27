import os
import sys
import glob
import asyncio
import logging
import importlib
from pathlib import Path
from pyrogram import idle
from aiohttp import web
from pyrogram.errors import BadMsgNotification
from pyrogram.types import BotCommand

from .bot import StreamBot
from .vars import Var
from .server import web_server
from .utils.keepalive import ping_server
from ShivamNox.bot.clients import initialize_clients

# ============ LOGGING CONFIGURATION ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
# ===============================================

logger = logging.getLogger(__name__)

ppath = "ShivamNox/bot/plugins/*.py"
files = glob.glob(ppath)

# Get event loop
loop = asyncio.get_event_loop()


async def start_bot_with_retry():
    """Start bot with retry logic"""
    for attempt in range(5):
        try:
            await StreamBot.start()
            return True
        except BadMsgNotification as e:
            logger.warning(f"Time sync error: {e}. Retry {attempt + 1}/5")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Start error: {e}")
            await asyncio.sleep(3)
    return False


async def set_bot_commands():
    """Set bot commands"""
    commands = [
        BotCommand("start", "🚀 Launch the bot"),
        BotCommand("about", "ℹ️ About this bot"),
        BotCommand("help", "❓ Get help"),
        BotCommand("terms", "📄 Terms & Conditions"),
        BotCommand("dmca", "📜 DMCA / Copyright Policy"),
        BotCommand("ping", "📶 Check responsiveness"),
        BotCommand("status", "📊 Bot status"),
        BotCommand("list", "📜 All commands"),
    ]
    try:
        await StreamBot.set_bot_commands(commands)
    except Exception as e:
        logger.warning(f"Failed to set commands: {e}")


async def start_services():
    """Main startup function"""
    print('\n')
    print('------------------- Initializing Telegram Bot -------------------')
    
    # Start bot
    if not await start_bot_with_retry():
        print("❌ Failed to start bot!")
        sys.exit(1)
    
    bot_info = await StreamBot.get_me()
    StreamBot.username = bot_info.username
    print(f"✅ Bot: @{StreamBot.username}")
    
    await set_bot_commands()
    print("------------------------------ DONE ------------------------------")
    
    # Initialize clients
    print("---------------------- Initializing Clients ----------------------")
    await initialize_clients()
    print("------------------------------ DONE ------------------------------")
    
    # Import plugins
    print('--------------------------- Importing ---------------------------')
    for name in files:
        try:
            with open(name) as a:
                patt = Path(a.name)
                plugin_name = patt.stem.replace(".py", "")
                plugins_dir = Path(f"ShivamNox/bot/plugins/{plugin_name}.py")
                import_path = ".plugins.{}".format(plugin_name)
                spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
                load = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(load)
                sys.modules["ShivamNox.bot.plugins." + plugin_name] = load
                print(f"Imported => {plugin_name}")
        except Exception as e:
            print(f"Failed => {plugin_name}: {e}")
    
    # Keep-alive
    if Var.ON_HEROKU:
        print("------------------ Starting Keep Alive Service ------------------")
        asyncio.create_task(ping_server())
    
    # Web server
    print('-------------------- Initializing Web Server --------------------')
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0" if Var.ON_HEROKU else Var.BIND_ADRESS
    await web.TCPSite(app, bind_address, Var.PORT).start()
    print('----------------------------- DONE ------------------------------')
    
    print('\n')
    print('----------------------- Service Started -------------------------')
    print(f'  Bot: @{StreamBot.username}')
    print(f'  Server: {bind_address}:{Var.PORT}')
    print(f'  Owner: {Var.OWNER_USERNAME}')
    if Var.ON_HEROKU:
        print(f'  URL: {Var.FQDN}')
    print('-----------------------------------------------------------------')
    
    # THIS IS IMPORTANT - Keep bot running
    await idle()


# ============ THIS IS THE CORRECT WAY TO RUN ============
if __name__ == '__main__':
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        logging.info('Service Stopped')
# ========================================================
