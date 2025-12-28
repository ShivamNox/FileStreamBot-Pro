# (c) ShivamNox
import asyncio
import logging
from ..vars import Var
from pyrogram import Client
from ShivamNox.utils.config_parser import TokenParser
from . import multi_clients, work_loads, StreamBot
from .channel_fix import ensure_bin_channel

logger = logging.getLogger(__name__)


async def initialize_clients():
    """Initialize all bot clients"""
    
    # Wait for main bot channel to be ready
    logger.info("⏳ Waiting for main bot to initialize...")
    
    if not await StreamBot.wait_channel_ready(timeout=120):
        logger.warning("⚠️ Main bot channel not ready, continuing anyway...")
    
    # Add main bot to clients
    multi_clients[0] = StreamBot
    work_loads[0] = 0
    
    # Parse additional tokens
    all_tokens = TokenParser().parse_from_env()
    if not all_tokens:
        print("No additional clients found, using default client")
        return
    
    async def start_client(client_id, token):
        """Start a single client with delay"""
        try:
            # Stagger client starts to avoid rate limits
            await asyncio.sleep(client_id * 2)
            
            print(f"Starting - Client {client_id}")
            
            client = await Client(
                name=str(client_id),
                api_id=Var.API_ID,
                api_hash=Var.API_HASH,
                bot_token=token,
                sleep_threshold=Var.SLEEP_THRESHOLD,
                no_updates=True,
                in_memory=True
            ).start()
            
            # Wait for connection to stabilize
            await asyncio.sleep(2)
            
            # Resolve channel for this client
            if await ensure_bin_channel(client, Var.BIN_CHANNEL):
                work_loads[client_id] = 0
                logger.info(f"✅ Client {client_id} ready")
                return client_id, client
            else:
                logger.warning(f"⚠️ Client {client_id} channel failed")
                await client.stop()
                return None
                
        except Exception as e:
            logger.error(f"Failed to start Client {client_id}: {e}")
            return None
    
    # Start clients sequentially to avoid rate limits
    for i, token in all_tokens.items():
        result = await start_client(i, token)
        if result:
            client_id, client = result
            multi_clients[client_id] = client
    
    if len(multi_clients) > 1:
        Var.MULTI_CLIENT = True
        print(f"Multi-Client Mode: {len(multi_clients)} clients active")
    else:
        print("Single client mode")
    
    logger.info(f"✅ Total active clients: {len(multi_clients)}")
