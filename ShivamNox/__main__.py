import os
import sys
import glob
import asyncio
import logging
import importlib
from pathlib import Path
from pyrogram import Client, idle
from .bot import StreamBot
from .vars import Var
from aiohttp import web
from .server import web_server
from .utils.keepalive import ping_server
from ShivamNox.bot.clients import initialize_clients
from pyrogram.errors import BadMsgNotification

# ============ ADD THESE LINES AT THE TOP ============
# Suppress socket warnings
logging.getLogger("asyncio").setLevel(logging.ERROR)
# ====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.WARNING)  # Changed from ERROR to WARNING
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

ppath = "ShivamNox/bot/plugins/*.py"
files = glob.glob(ppath)

# ============ FIXED: Use new asyncio API ============
# loop = asyncio.get_event_loop()  # OLD - Deprecated
# ====================================================

# ============ FIXED: Don't delete session every time! ============
async def reset_session():
    """Only reset session if there's a specific auth error"""
    # Don't delete session on every start!
    # This was causing reconnection issues
    pass
    # session_file = "Web Streamer.session"
    # if os.path.exists(session_file):
    #     os.remove(session_file)
    #     print(f"Session file {session_file} deleted.")
# =================================================================

async def start_bot_with_retry():
    retry_count = 0
    max_retries = 5
    while retry_count < max_retries:
        try:
            await StreamBot.start()
            break
        except BadMsgNotification as e:
            print(f"Time synchronization error: {e}. Retrying... ({retry_count + 1}/{max_retries})")
            retry_count += 1
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise  # Re-raise to see the actual error
    else:
        print("Max retries reached. Please check your server time or network.")
        sys.exit(1)

from pyrogram.types import BotCommand

async def set_bot_commands():
    commands = [
        BotCommand("start", "🚀 Launch the bot and explore its features"),
        BotCommand("ping", "📶 Check the bot's responsiveness"),
        BotCommand("about", "ℹ️ Discover more about this bot"),
        BotCommand("status", "📊 View the current status of the bot"),
        BotCommand("list", "📜 Get a list of all available commands"),
        BotCommand("dc", "🔗 Disconnect from the bot or service"),
        BotCommand("subscribe", "🔔 Subscribe to get updates and notifications"),
        BotCommand("maintainers", "🔗 Disconnect from the bot or service")
    ]
    await StreamBot.set_bot_commands(commands)


async def start_services():
    print('\n')
    print('------------------- Initializing Telegram Bot -------------------')
    
    # Don't reset session every time
    # await reset_session()
    
    await start_bot_with_retry()
    bot_info = await StreamBot.get_me()
    StreamBot.username = bot_info.username
    
    await set_bot_commands()

    print("------------------------------ DONE ------------------------------")
    print()
    print("---------------------- Initializing Clients ----------------------")
    await initialize_clients()
    print("------------------------------ DONE ------------------------------")
    print('\n')
    print('--------------------------- Importing ---------------------------')
    
    for name in files:
        with open(name) as a:
            patt = Path(a.name)
            plugin_name = patt.stem.replace(".py", "")
            plugins_dir = Path(f"ShivamNox/bot/plugins/{plugin_name}.py")
            import_path = ".plugins.{}".format(plugin_name)
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            load = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(load)
            sys.modules["ShivamNox.bot.plugins." + plugin_name] = load
            print("Imported => " + plugin_name)
    
    print('-------------------- Initializing Web Server -------------------------')
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0" if Var.ON_HEROKU else Var.BIND_ADRESS
    await web.TCPSite(app, bind_address, Var.PORT).start()
    print('----------------------------- DONE ----------------------------------')
    
    # ============ FIXED: Start keep-alive AFTER everything is ready ============
    if Var.ON_HEROKU:
        print("------------------ Starting Keep Alive Service ------------------")
        # Add delay before starting ping service
        await asyncio.sleep(10)  # Wait 10 seconds for connections to stabilize
        asyncio.create_task(ping_server())
    # ===========================================================================
    
    print('\n')
    print('---------------------------------------------------------------------------------------------------------')
    print(' follow me for more such exciting bots! https://github.com/ShivamNox')
    print('---------------------------------------------------------------------------------------------------------')
    print('\n')
    print('----------------------- Service Started -----------------------------------------------------------------')
    print('                        bot =>> {}'.format((await StreamBot.get_me()).first_name))
    print('                        server ip =>> {}:{}'.format(bind_address, Var.PORT))
    print('                        Owner =>> {}'.format((Var.OWNER_USERNAME)))
    if Var.ON_HEROKU:
        print('                        app running on =>> {}'.format(Var.FQDN))
    print('---------------------------------------------------------------------------------------------------------')
    print('Give a star to my repo https://github.com/ShivamNox/filestreambot-pro  also follow me for new bots')
    print('---------------------------------------------------------------------------------------------------------')
    
    await idle()


if __name__ == '__main__':
    try:
        # ============ FIXED: Use asyncio.run() instead of deprecated method ============
        asyncio.run(start_services())
        # ================================================================================
    except KeyboardInterrupt:
        logging.info('----------------------- Service Stopped -----------------------')
