# (c) ShivamNox
import asyncio
import logging
from ..vars import Var
from pyrogram import Client
from ShivamNox.utils.config_parser import TokenParser
from . import multi_clients, work_loads, StreamBot
from .channel_fix import ensure_bin_channel

# Suppress asyncio socket warnings
logging.getLogger('asyncio').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


async def initialize_clients():
    # Wait for main bot channel to be ready
    logger.info("⏳ Waiting for main bot to initialize...")
    
    if not await StreamBot.wait_channel_ready(timeout=120):
        logger.warning("⚠️ Main bot channel not ready, continuing anyway...")
    
    multi_clients[0] = StreamBot
    work_loads[0] = 0
    
    all_tokens = TokenParser().parse_from_env()
    if not all_tokens:
        print("No additional clients found, using default client")
        return
    
    async def start_client(client_id, token):
        try:
            # ============ ADD DELAY BETWEEN CLIENT STARTS ============
            await asyncio.sleep(client_id * 3)  # Stagger client starts by 3 seconds each
            # ==========================================================
            
            print(f"Starting - Client {client_id}")
            if client_id == len(all_tokens):
                await asyncio.sleep(2)
                print("This will take some time, please wait...")
            
            client = await Client(
                name=str(client_id),
                api_id=Var.API_ID,
                api_hash=Var.API_HASH,
                bot_token=token,
                sleep_threshold=Var.SLEEP_THRESHOLD,
                no_updates=True,
                in_memory=True
            ).start()
            
            # Small delay after start
            await asyncio.sleep(2)
            
            # Resolve channel for this client too
            if await ensure_bin_channel(client, Var.BIN_CHANNEL):
                work_loads[client_id] = 0
                logger.info(f"✅ Client {client_id} channel resolved")
                return client_id, client
            else:
                logger.warning(f"⚠️ Client {client_id} channel failed, stopping...")
                await client.stop()
                return None
                
        except Exception:
            logging.error(f"Failed starting Client - {client_id} Error:", exc_info=True)
            return None
    
    # ============ START CLIENTS SEQUENTIALLY INSTEAD OF PARALLEL ============
    valid_clients = {}
    for i, token in all_tokens.items():
        result = await start_client(i, token)
        if result:
            client_id, client = result
            valid_clients[client_id] = client
    # =========================================================================
    
    multi_clients.update(valid_clients)
    
    if len(multi_clients) != 1:
        Var.MULTI_CLIENT = True
        print("Multi-Client Mode Enabled")
    else:
        print("No additional clients were initialized, using default client")
    
    logger.info(f"✅ Total active clients: {len(multi_clients)}")
