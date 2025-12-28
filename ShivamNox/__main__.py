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

# ============ LOGGING CONFIGURATION (ONLY ONCE) ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Suppress noisy loggers
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("aiohttp.web").setLevel(logging.WARNING)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pyrogram.session").setLevel(logging.WARNING)
logging.getLogger("pyrogram.connection").setLevel(logging.WARNING)
# ===========================================================

from .bot import StreamBot
from .vars import Var
from .server import web_server
from .utils.keepalive import ping_server
from ShivamNox.bot.clients import initialize_clients

logger = logging.getLogger(__name__)

ppath = "ShivamNox/bot/plugins/*.py"
files = glob.glob(ppath)


async def start_bot_with_retry():
    """Start bot with retry logic for time sync errors"""
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
    
    logger.error("Max retries reached. Could not start bot.")
    return False


async def set_bot_commands():
    """Set bot commands"""
    commands = [
        BotCommand("start", "🚀 Launch the bot and explore its features"),
        BotCommand("ping", "📶 Check the bot's responsiveness"),
        BotCommand("about", "ℹ️ Discover more about this bot"),
        BotCommand("status", "📊 View the current status of the bot"),
        BotCommand("list", "📜 Get a list of all available commands"),
        BotCommand("dc", "🔗 Disconnect from the bot or service"),
        BotCommand("subscribe", "🔔 Subscribe to get updates and notifications"),
        BotCommand("maintainers", "🔗 Bot maintainers info")
    ]
    try:
        await StreamBot.set_bot_commands(commands)
    except Exception as e:
        logger.warning(f"Failed to set commands: {e}")


async def start_services():
    """Main startup function"""
    print('\n')
    print('=' * 65)
    print('          FileStreamBot Pro - Starting...                     ')
    print('=' * 65)
    
    # Start bot
    print('\n[1/5] 🤖 Starting Telegram Bot...')
    if not await start_bot_with_retry():
        print("❌ Failed to start bot!")
        sys.exit(1)
    
    bot_info = await StreamBot.get_me()
    StreamBot.username = bot_info.username
    print(f"✅ Bot started as @{StreamBot.username}")
    
    # Set commands
    await set_bot_commands()
    
    # Initialize clients
    print('\n[2/5] 👥 Initializing Clients...')
    await initialize_clients()
    print("✅ Clients initialized")
    
    # Import plugins
    print('\n[3/5] 🔌 Loading Plugins...')
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
                print(f"   ✅ {plugin_name}")
        except Exception as e:
            print(f"   ❌ {plugin_name}: {e}")
    
    # Start web server
    print('\n[4/5] 🌐 Starting Web Server...')
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0" if Var.ON_HEROKU else Var.BIND_ADRESS
    await web.TCPSite(app, bind_address, Var.PORT).start()
    print(f"✅ Server running on {bind_address}:{Var.PORT}")
    
    # Start keep-alive
    if Var.ON_HEROKU:
        print('\n[5/5] 💓 Starting Keep-Alive Service...')
        asyncio.create_task(ping_server())
        print("✅ Keep-alive started")
    else:
        print('\n[5/5] 💓 Keep-Alive: Skipped (not on Heroku/Render)')
    
    # Print startup summary
    print('\n')
    print('=' * 65)
    print('           🎉 SERVICE STARTED SUCCESSFULLY 🎉                  ')
    print('=' * 65)
    print(f'   Bot      : @{StreamBot.username}')
    print(f'   Name     : {bot_info.first_name}')
    print(f'   Server   : http://{bind_address}:{Var.PORT}')
    print(f'   Owner    : {Var.OWNER_USERNAME}')
    if Var.ON_HEROKU:
        print(f'   URL      : https://{Var.FQDN}')
    print('=' * 65)
    print('   GitHub: https://github.com/ShivamNox/FileStreamBot-Pro')
    print('=' * 65)
    print('\n')
    
    await idle()


if __name__ == '__main__':
    try:
        # Use asyncio.run() for Python 3.7+
        asyncio.run(start_services())
    except KeyboardInterrupt:
        logger.info('Service stopped by user')
    except Exception as e:
        logger.error(f'Service crashed: {e}')
        import traceback
        traceback.print_exc()
