# (c) ShivamNox
import logging
import asyncio
from pyrogram import Client
import pyromod.listen
from ..vars import Var

logger = logging.getLogger(__name__)


class StreamBotClient(Client):
    def __init__(self):
        super().__init__(
            name='WebStreamer',
            api_id=Var.API_ID,
            api_hash=Var.API_HASH,
            bot_token=Var.BOT_TOKEN,
            sleep_threshold=Var.SLEEP_THRESHOLD,
            workers=Var.WORKERS
        )
        self.username = None
        self.me = None
        self._channel_ready = asyncio.Event()
    
    async def start(self):
        await super().start()
        self.me = await self.get_me()
        self.username = self.me.username
        logger.info(f"✅ Bot started as @{self.username}")
        
        # Wait for connection to stabilize
        await asyncio.sleep(2)
        
        # Resolve BIN_CHANNEL with retry
        from .channel_fix import ensure_bin_channel
        
        for attempt in range(3):
            logger.info(f"🔄 Resolving BIN_CHANNEL (attempt {attempt + 1}/3)")
            if await ensure_bin_channel(self, Var.BIN_CHANNEL):
                self._channel_ready.set()
                logger.info("✅ BIN_CHANNEL is ready!")
                break
            await asyncio.sleep(5)
        else:
            logger.error("❌ Failed to resolve BIN_CHANNEL after 3 attempts")
            logger.error(f"Make sure bot is admin in channel ID: {Var.BIN_CHANNEL}")
        
        return self
    
    async def wait_channel_ready(self, timeout=60):
        """Wait for channel to be ready"""
        try:
            await asyncio.wait_for(self._channel_ready.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            return False
    
    def is_channel_ready(self):
        """Check if channel is ready"""
        return self._channel_ready.is_set()


StreamBot = StreamBotClient()
multi_clients = {}
work_loads = {}
