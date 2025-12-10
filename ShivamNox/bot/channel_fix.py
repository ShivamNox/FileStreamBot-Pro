# (c) ShivamNox - Channel Resolution Fix
import asyncio
import logging
from pyrogram import Client
from pyrogram.errors import ChannelPrivate, FloodWait
from pyrogram.raw import functions, types

logger = logging.getLogger(__name__)


class BinChannelManager:
    _resolved: bool = False
    _channel_id: int = None
    _channel_title: str = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def resolve(cls, client: Client, channel_id: int, force: bool = False) -> bool:
        async with cls._lock:
            if cls._resolved and cls._channel_id == channel_id and not force:
                return True
            
            cls._channel_id = channel_id
            logger.info(f"🔄 Starting BIN_CHANNEL resolution for: {channel_id}")
            
            channel_str = str(channel_id)
            if channel_str.startswith("-100"):
                real_id = int(channel_str[4:])
            else:
                real_id = abs(channel_id)
            
            logger.info(f"📍 Real channel ID: {real_id}")
            
            methods = [
                ("Direct Send", cls._method_direct_send),
                ("Get Chat", cls._method_get_chat),
                ("Resolve Peer", cls._method_resolve_peer),
                ("Raw API GetChannels", cls._method_raw_get_channels),
            ]
            
            for method_name, method_func in methods:
                try:
                    logger.info(f"🔧 Trying method: {method_name}")
                    success = await method_func(client, channel_id, real_id)
                    if success:
                        cls._resolved = True
                        logger.info(f"✅ SUCCESS with method: {method_name}")
                        logger.info(f"✅ Channel: {cls._channel_title} (ID: {channel_id})")
                        return True
                except FloodWait as e:
                    await asyncio.sleep(e.value + 1)
                except ChannelPrivate:
                    logger.error("❌ Bot not member of channel!")
                    return False
                except Exception:
                    continue
            
            logger.error("❌ All resolution methods failed!")
            return False
    
    @classmethod
    async def _method_direct_send(cls, client, channel_id, real_id) -> bool:
        msg = await client.send_message(channel_id, "🔄")
        await msg.delete()
        chat = await client.get_chat(channel_id)
        cls._channel_title = chat.title
        return True
    
    @classmethod
    async def _method_get_chat(cls, client, channel_id, real_id) -> bool:
        chat = await client.get_chat(channel_id)
        cls._channel_title = chat.title
        msg = await client.send_message(channel_id, "✅")
        await msg.delete()
        return True
    
    @classmethod
    async def _method_resolve_peer(cls, client, channel_id, real_id) -> bool:
        await client.resolve_peer(channel_id)
        chat = await client.get_chat(channel_id)
        cls._channel_title = chat.title
        return True
    
    @classmethod
    async def _method_raw_get_channels(cls, client, channel_id, real_id) -> bool:
        try:
            peer = await client.resolve_peer(channel_id)
            access_hash = peer.access_hash if hasattr(peer, 'access_hash') else 0
        except Exception:
            access_hash = 0
        
        input_channel = types.InputChannel(channel_id=real_id, access_hash=access_hash)
        result = await client.invoke(functions.channels.GetChannels(id=[input_channel]))
        
        if result.chats:
            cls._channel_title = result.chats[0].title
            await client.resolve_peer(channel_id)
            return True
        return False
    
    @classmethod
    def is_resolved(cls) -> bool:
        return cls._resolved
    
    @classmethod
    def reset(cls):
        cls._resolved = False
        cls._channel_title = None


async def ensure_bin_channel(client: Client, channel_id: int) -> bool:
    return await BinChannelManager.resolve(client, channel_id)


def reset_bin_channel():
    BinChannelManager.reset()
