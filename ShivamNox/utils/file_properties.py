# (c) ShivamNox
from pyrogram import Client
from pyrogram.errors import PeerIdInvalid, ChannelInvalid
from typing import Any, Optional
from pyrogram.types import Message
from pyrogram.file_id import FileId
from pyrogram.raw.types.messages import Messages
from ShivamNox.server.exceptions import FIleNotFound
from ShivamNox.vars import Var
import asyncio
import logging

logger = logging.getLogger(__name__)


async def parse_file_id(message: "Message") -> Optional[FileId]:
    media = get_media_from_message(message)
    if media:
        return FileId.decode(media.file_id)


async def parse_file_unique_id(message: "Messages") -> Optional[str]:
    media = get_media_from_message(message)
    if media:
        return media.file_unique_id


async def get_file_ids(client: Client, chat_id: int, id: int) -> Optional[FileId]:
    # Ensure channel is resolved
    if chat_id == Var.BIN_CHANNEL:
        try:
            from ShivamNox.bot.channel_fix import ensure_bin_channel
            await ensure_bin_channel(client, chat_id)
        except Exception as e:
            logger.warning(f"Channel check warning: {e}")
    
    try:
        message = await client.get_messages(chat_id, id)
        
        if message.empty:
            raise FIleNotFound
        
        media = get_media_from_message(message)
        if not media:
            raise FIleNotFound
        
        file_unique_id = await parse_file_unique_id(message)
        file_id = await parse_file_id(message)
        
        setattr(file_id, "file_size", getattr(media, "file_size", 0))
        setattr(file_id, "mime_type", getattr(media, "mime_type", ""))
        setattr(file_id, "file_name", getattr(media, "file_name", ""))
        setattr(file_id, "unique_id", file_unique_id)
        
        return file_id
        
    except (PeerIdInvalid, ChannelInvalid) as e:
        logger.warning(f"⚠️ Peer error: {e}, retrying...")
        
        from ShivamNox.bot.channel_fix import reset_bin_channel, ensure_bin_channel
        reset_bin_channel()
        await asyncio.sleep(2)
        
        if await ensure_bin_channel(client, chat_id):
            message = await client.get_messages(chat_id, id)
            
            if message.empty:
                raise FIleNotFound
            
            media = get_media_from_message(message)
            if not media:
                raise FIleNotFound
            
            file_unique_id = await parse_file_unique_id(message)
            file_id = await parse_file_id(message)
            
            setattr(file_id, "file_size", getattr(media, "file_size", 0))
            setattr(file_id, "mime_type", getattr(media, "mime_type", ""))
            setattr(file_id, "file_name", getattr(media, "file_name", ""))
            setattr(file_id, "unique_id", file_unique_id)
            
            return file_id
        
        raise FIleNotFound


def get_media_from_message(message: "Message") -> Any:
    media_types = (
        "audio",
        "document",
        "photo",
        "sticker",
        "animation",
        "video",
        "voice",
        "video_note",
    )
    for attr in media_types:
        media = getattr(message, attr, None)
        if media:
            return media


def get_hash(media_msg: Message) -> str:
    media = get_media_from_message(media_msg)
    return getattr(media, "file_unique_id", "")[:6]


def get_name(media_msg: Message) -> str:
    media = get_media_from_message(media_msg)
    return getattr(media, 'file_name', "")


def get_media_file_size(m):
    media = get_media_from_message(m)
    return getattr(media, "file_size", 0)
