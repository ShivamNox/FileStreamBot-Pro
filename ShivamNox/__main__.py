import os
import sys
import glob
import asyncio
import logging
import signal
import importlib
from pathlib import Path
from pyrogram import idle
from aiohttp import web
from pyrogram.errors import BadMsgNotification
from pyrogram.types import BotCommand

# ============ SUPPRESS WARNINGS FIRST ============
logging.getLogger("asyncio").setLevel(logging.ERROR)
# =================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

# ============ HANDLE SIGNALS ============
startup_complete = False

def signal_handler(sig, frame):
    global startup_complete
    if not startup_complete:
        logger.warning(f"Ignoring signal {sig} during startup...")
        return
    logger.info("Shutting down...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
# ========================================

# Import AFTER signal handlers are set
from ShivamNox.bot import StreamBot
from ShivamNox.vars import Var
from ShivamNox.server import web_server
from ShivamNox.utils.keepalive import ping_server
from ShivamNox.bot.clients import initialize_clients

ppath = "ShivamNox/bot/plugins/*.py"
files = glob.glob(ppath)


async def start_bot_with_retry():
    retry_count = 0
    max_retries = 5
    while retry_count < max_retries:
        try:
            await StreamBot.start()
            return True
        except BadMsgNotification as e:
            logger.warning(f"Time sync error: {e}. Retry {retry_count + 1}/{max_retries}")
            retry_count += 1
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Start error: {e}")
            import traceback
            traceback.print_exc()
            retry_count += 1
            await asyncio.sleep(3)
    
    logger.error("Max retries reached!")
    return False


async def set_bot_commands():
    commands = [
        BotCommand("start", "🚀 Launch the bot"),
        BotCommand("ping", "📶 Check responsiveness"),
        BotCommand("about", "ℹ️ About this bot"),
        BotCommand("status", "📊 Bot status"),
        BotCommand("list", "📜 All commands"),
        BotCommand("help", "❓ Get help"),
    ]
    try:
        await StreamBot.set_bot_commands(commands)
    except Exception as e:
        logger.warning(f"Failed to set commands: {e}")


def import_plugins():
    """Import all plugins AFTER bot is started"""
    print('--------------------------- Importing Plugins ---------------------------')
    for name in files:
        try:
            with open(name) as a:
                patt = Path(a.name)
                plugin_name = patt.stem.replace(".py", "")
                plugins_dir = Path(f"ShivamNox/bot/plugins/{plugin_name}.py")
                import_path = "ShivamNox.bot.plugins.{}".format(plugin_name)
                
                spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
                load = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(load)
                sys.modules[import_path] = load
                print(f"✅ Imported => {plugin_name}")
        except Exception as e:
            print(f"❌ Failed to import {name}: {e}")
            import traceback
            traceback.print_exc()
    print('----------------------------- DONE -------------------------------------')


async def start_services():
    global startup_complete
    
    print('\n')
    print('=================== FileStreamBot Pro ===================')
    print('------------------- Initializing Bot -------------------')
    
    if not await start_bot_with_retry():
        print("❌ Failed to start bot!")
        sys.exit(1)
    
    bot_info = await StreamBot.get_me()
    StreamBot.username = bot_info.username
    print(f"✅ Bot started as @{StreamBot.username}")
    
    print("------------------------------ DONE ------------------------------")
    
    # ============ IMPORT PLUGINS AFTER BOT STARTS ============
    import_plugins()
    # =========================================================
    
    print("---------------------- Initializing Clients ----------------------")
    await initialize_clients()
    print("------------------------------ DONE ------------------------------")
    
    await set_bot_commands()
    
    print('-------------------- Initializing Web Server --------------------')
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0" if Var.ON_HEROKU else Var.BIND_ADRESS
    await web.TCPSite(app, bind_address, Var.PORT).start()
    print('----------------------------- DONE ------------------------------')
    
    # Start keep-alive after everything is ready
    if Var.ON_HEROKU:
        print("------------------ Starting Keep Alive Service ------------------")
        await asyncio.sleep(5)
        asyncio.create_task(ping_server())
    
    # Mark startup complete - now signals will work
    startup_complete = True
    
    print('\n')
    print('=' * 70)
    print(f'  ✅ Bot: @{StreamBot.username}')
    print(f'  ✅ Server: http://{bind_address}:{Var.PORT}')
    print(f'  ✅ Owner: {Var.OWNER_USERNAME}')
    if Var.ON_HEROKU:
        print(f'  ✅ URL: {Var.FQDN}')
    print('=' * 70)
    print('  🎉 Bot is now READY and listening for messages!')
    print('=' * 70)
    print('\n')
    
    await idle()


if __name__ == '__main__':
    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        logger.info('Service stopped by user')
    except Exception as e:
        logger.error(f'Service crashed: {e}')
        import traceback
        traceback.print_exc()
