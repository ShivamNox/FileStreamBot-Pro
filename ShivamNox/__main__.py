import os
import sys
import glob
import asyncio
import logging
import signal
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
from pyrogram.types import BotCommand

# ============ SUPPRESS WARNINGS ============
logging.getLogger("asyncio").setLevel(logging.ERROR)
# ===========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

ppath = "ShivamNox/bot/plugins/*.py"
files = glob.glob(ppath)

# ============ HANDLE SIGNALS PROPERLY ============
def handle_signal(sig, frame):
    """Ignore signals during startup"""
    logging.warning(f"Received signal {sig}, ignoring during startup...")

# Temporarily ignore SIGTERM during startup
original_sigterm = signal.signal(signal.SIGTERM, handle_signal)
# =================================================


async def start_bot_with_retry():
    retry_count = 0
    max_retries = 5
    while retry_count < max_retries:
        try:
            await StreamBot.start()
            return True
        except BadMsgNotification as e:
            print(f"Time synchronization error: {e}. Retrying... ({retry_count + 1}/{max_retries})")
            retry_count += 1
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            retry_count += 1
            await asyncio.sleep(3)
    
    print("Max retries reached. Please check your server time or network.")
    return False


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
    try:
        await StreamBot.set_bot_commands(commands)
    except Exception as e:
        logging.warning(f"Failed to set commands: {e}")


async def start_services():
    global original_sigterm
    
    print('\n')
    print('------------------- Initializing Telegram Bot -------------------')
    
    if not await start_bot_with_retry():
        print("Failed to start bot!")
        sys.exit(1)
    
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
                print("Imported => " + plugin_name)
        except Exception as e:
            print(f"Failed to import {name}: {e}")
    
    print('-------------------- Initializing Web Server -------------------------')
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0" if Var.ON_HEROKU else Var.BIND_ADRESS
    await web.TCPSite(app, bind_address, Var.PORT).start()
    print('----------------------------- DONE ----------------------------------')
    
    # Start keep-alive after delay
    if Var.ON_HEROKU:
        print("------------------ Starting Keep Alive Service ------------------")
        await asyncio.sleep(5)
        asyncio.create_task(ping_server())
    
    print('\n')
    print('---------------------------------------------------------------------------------------------------------')
    print(' follow me for more such exciting bots! https://github.com/ShivamNox')
    print('---------------------------------------------------------------------------------------------------------')
    print('\n')
    print('----------------------- Service Started -----------------------------------------------------------------')
    print('                        bot =>> {}'.format(bot_info.first_name))
    print('                        server ip =>> {}:{}'.format(bind_address, Var.PORT))
    print('                        Owner =>> {}'.format((Var.OWNER_USERNAME)))
    if Var.ON_HEROKU:
        print('                        app running on =>> {}'.format(Var.FQDN))
    print('---------------------------------------------------------------------------------------------------------')
    
    # ============ RESTORE SIGNAL HANDLER AFTER STARTUP ============
    signal.signal(signal.SIGTERM, original_sigterm)
    logging.info("✅ Bot is now fully ready and listening for messages!")
    # ==============================================================
    
    await idle()


if __name__ == '__main__':
    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        logging.info('Service Stopped by user')
    except Exception as e:
        logging.error(f'Service crashed: {e}')
        import traceback
        traceback.print_exc()
