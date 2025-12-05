# (c) ShivamNox
from pyrogram import Client
import pyromod.listen
from ..vars import Var
from os import getcwd
import asyncio
import logging

logger = logging.getLogger(__name__)


class StreamBotClient(Client):
    def __init__(self):
        super().__init__(
            name='Web Streamer',
            api_id=Var.API_ID,
            api_hash=Var.API_HASH,
            bot_token=Var.BOT_TOKEN,
            sleep_threshold=Var.SLEEP_THRESHOLD,
            workers=Var.WORKERS
        )
    
    async def start(self):
        await super().start()
        
        # ✅ FIX: Force cache BIN_CHANNEL on startup
        try:
            # Method 1: Try to send and delete a message
            msg = await self.send_message(Var.BIN_CHANNEL, "🔄 Initializing bot...")
            await msg.delete()
            logger.info(f"✅ BIN_CHANNEL resolved successfully")
        except Exception as e:
            logger.warning(f"First attempt failed: {e}")
            
            # Method 2: Get all dialogs to cache everything
            try:
                me = await self.get_me()
                # For bots, we need to iterate through chats differently
                # Try to access using raw API
                from pyrogram.raw import functions
                result = await self.invoke(
                    functions.messages.GetDialogs(
                        offset_date=0,
                        offset_id=0,
                        offset_peer=await self.resolve_peer("me"),
                        limit=100,
                        hash=0
                    )
                )
                logger.info(f"✅ Loaded {len(result.chats)} chats")
                
                # Now try again
                msg = await self.send_message(Var.BIN_CHANNEL, "✅")
                await msg.delete()
                logger.info(f"✅ BIN_CHANNEL resolved after loading chats")
            except Exception as e2:
                logger.error(f"❌ Cannot resolve BIN_CHANNEL: {e2}")
                logger.error(f"Make sure bot is admin in channel ID: {Var.BIN_CHANNEL}")
        
        return self


StreamBot = StreamBotClient()

multi_clients = {}
work_loads = {}
