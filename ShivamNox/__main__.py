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

logging.getLogger("asyncio").setLevel(logging.CRITICAL)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

ppath = "ShivamNox/bot/plugins/*.py"
files = glob.glob(ppath)
loop = asyncio.get_event_loop()

# Utility to ensure session file deletion and re-login
async def reset_session():
    session_file = "ShivamNox.session"  # Replace with the actual session name
    if os.path.exists(session_file):
        os.remove(session_file)
        print(f"Session file {session_file} deleted. Please log in again.")

async def start_bot_with_retry():
    retry_count = 0
    max_retries = 5
    while retry_count < max_retries:
        try:
            await StreamBot.start()
            break  # Exit the loop if successful
        except BadMsgNotification as e:
            print(f"Time synchronization error: {e}. Retrying... ({retry_count + 1}/{max_retries})")
            retry_count += 1
            await asyncio.sleep(5)  # Wait before retrying
        except Exception as e:
            print(f"Unexpected error: {e}")
            break  # Exit the loop for other errors
    else:
        print("Max retries reached. Please check your server time or network.")

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
    
    await reset_session()  # Ensure no previous session conflicts
    await start_bot_with_retry()  # Start bot with retry logic
    bot_info = await StreamBot.get_me()
    StreamBot.username = bot_info.username
    
    # Set bot commands
    await set_bot_commands()

    print("------------------------------ DONE ------------------------------")
    print()
    print(
        "---------------------- Initializing Clients ----------------------"
    )
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
    if Var.ON_HEROKU:
        print("------------------ Starting Keep Alive Service ------------------")
        print()
        asyncio.create_task(ping_server())
    print('-------------------- Initializing Web Server -------------------------')
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0" if Var.ON_HEROKU else Var.BIND_ADRESS
    await web.TCPSite(app, bind_address, Var.PORT).start()
    print('----------------------------- DONE ---------------------------------------------------------------------')
    print('\n')
    print('---------------------------------------------------------------------------------------------------------')
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
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        logging.info('----------------------- Service Stopped -----------------------')
