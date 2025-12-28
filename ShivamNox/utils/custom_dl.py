# (c) ShivamNox - Fixed for high traffic
import math
import asyncio
import logging
from ShivamNox.vars import Var
from typing import Dict, Union, Optional
from ShivamNox.bot import work_loads
from pyrogram import Client, utils, raw
from .file_properties import get_file_ids
from pyrogram.session import Session, Auth
from pyrogram.errors import AuthBytesInvalid, PeerIdInvalid, ChannelInvalid, FloodWait
from ShivamNox.server.exceptions import FIleNotFound
from pyrogram.file_id import FileId, FileType, ThumbnailSource
from collections import OrderedDict
import time

# Suppress connection error logs
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("pyrogram.session").setLevel(logging.WARNING)
logging.getLogger("pyrogram.connection").setLevel(logging.WARNING)
# ==========================================

logger = logging.getLogger(__name__)


class LRUCache:
    """Thread-safe LRU Cache with expiration"""
    def __init__(self, maxsize: int = 1000, ttl: int = 3600):
        self.cache: OrderedDict = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl  # Time to live in seconds
        self._lock = asyncio.Lock()
    
    async def get(self, key):
        async with self._lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    self.cache.move_to_end(key)
                    return value
                else:
                    del self.cache[key]
            return None
    
    async def set(self, key, value):
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
            elif len(self.cache) >= self.maxsize:
                self.cache.popitem(last=False)
            self.cache[key] = (value, time.time())
    
    async def clear(self):
        async with self._lock:
            self.cache.clear()


class MediaSessionPool:
    """Connection pool for media sessions"""
    def __init__(self, max_sessions_per_dc: int = 5):
        self.sessions: Dict[int, list] = {}  # dc_id -> list of sessions
        self.max_sessions = max_sessions_per_dc
        self._locks: Dict[int, asyncio.Lock] = {}
        self._creating: Dict[int, bool] = {}
    
    def _get_lock(self, dc_id: int) -> asyncio.Lock:
        if dc_id not in self._locks:
            self._locks[dc_id] = asyncio.Lock()
        return self._locks[dc_id]
    
    async def get_session(self, client: Client, file_id: FileId) -> Session:
        """Get or create a media session from the pool"""
        dc_id = file_id.dc_id
        
        async with self._get_lock(dc_id):
            # Check if we have an existing session
            if dc_id in self.sessions and self.sessions[dc_id]:
                # Return least used session (round-robin would be better)
                return self.sessions[dc_id][0]
            
            # Create new session
            session = await self._create_session(client, file_id)
            
            if dc_id not in self.sessions:
                self.sessions[dc_id] = []
            
            if len(self.sessions[dc_id]) < self.max_sessions:
                self.sessions[dc_id].append(session)
            
            return session
    
    async def _create_session(self, client: Client, file_id: FileId) -> Session:
        """Create a new media session"""
        dc_id = file_id.dc_id
        
        # Check if client already has a session for this DC
        if dc_id in client.media_sessions:
            return client.media_sessions[dc_id]
        
        if dc_id != await client.storage.dc_id():
            media_session = Session(
                client,
                dc_id,
                await Auth(client, dc_id, await client.storage.test_mode()).create(),
                await client.storage.test_mode(),
                is_media=True,
            )
            await media_session.start()

            for attempt in range(6):
                try:
                    exported_auth = await client.invoke(
                        raw.functions.auth.ExportAuthorization(dc_id=dc_id)
                    )
                    await media_session.send(
                        raw.functions.auth.ImportAuthorization(
                            id=exported_auth.id, bytes=exported_auth.bytes
                        )
                    )
                    break
                except AuthBytesInvalid:
                    if attempt == 5:
                        await media_session.stop()
                        raise
                    await asyncio.sleep(1)
        else:
            media_session = Session(
                client,
                dc_id,
                await client.storage.auth_key(),
                await client.storage.test_mode(),
                is_media=True,
            )
            await media_session.start()
        
        client.media_sessions[dc_id] = media_session
        logger.debug(f"Created media session for DC {dc_id}")
        return media_session
    
    async def close_all(self):
        """Close all sessions"""
        for dc_id, sessions in self.sessions.items():
            for session in sessions:
                try:
                    await session.stop()
                except Exception:
                    pass
        self.sessions.clear()


# Global instances
_file_cache = LRUCache(maxsize=2000, ttl=3600)
_session_pool = MediaSessionPool(max_sessions_per_dc=3)


class ByteStreamer:
    def __init__(self, client: Client):
        """A custom class that holds the cache of a specific client and class functions."""
        self.client: Client = client
        self.cached_file_ids: Dict[int, FileId] = {}
        # Use global cache instead of per-instance
        self._cache = _file_cache
        self._session_pool = _session_pool

    async def get_file_properties(self, id: int) -> FileId:
        """Get file properties with caching"""
        # Check global cache first
        cached = await self._cache.get(f"{id}")
        if cached:
            return cached
        
        # Check local cache
        if id in self.cached_file_ids:
            return self.cached_file_ids[id]
        
        # Generate new
        file_id = await self.generate_file_properties(id)
        return file_id

    async def generate_file_properties(self, id: int) -> FileId:
        """Generate file properties with retry logic"""
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Ensure channel is resolved
                from ShivamNox.bot.channel_fix import ensure_bin_channel
                await ensure_bin_channel(self.client, Var.BIN_CHANNEL)
                
                file_id = await get_file_ids(self.client, Var.BIN_CHANNEL, id)
                
                if not file_id:
                    raise FIleNotFound
                
                # Cache in both local and global cache
                self.cached_file_ids[id] = file_id
                await self._cache.set(f"{id}", file_id)
                
                return file_id
                
            except (PeerIdInvalid, ChannelInvalid) as e:
                logger.warning(f"Peer error (attempt {attempt + 1}/{max_retries}): {e}")
                from ShivamNox.bot.channel_fix import reset_bin_channel
                reset_bin_channel()
                last_error = e
                await asyncio.sleep(2 ** attempt)
                
            except FloodWait as e:
                logger.warning(f"FloodWait: sleeping {e.value}s")
                await asyncio.sleep(e.value)
                
            except FIleNotFound:
                raise
                
            except Exception as e:
                logger.error(f"Error generating file properties: {e}")
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
        
        logger.error(f"Failed after {max_retries} attempts: {last_error}")
        raise FIleNotFound

    async def generate_media_session(self, client: Client, file_id: FileId) -> Session:
        """Get media session from pool"""
        return await self._session_pool.get_session(client, file_id)

    @staticmethod
    async def get_location(file_id: FileId) -> Union[
        raw.types.InputPhotoFileLocation,
        raw.types.InputDocumentFileLocation,
        raw.types.InputPeerPhotoFileLocation,
    ]:
        """Get file location for download"""
        file_type = file_id.file_type

        if file_type == FileType.CHAT_PHOTO:
            if file_id.chat_id > 0:
                peer = raw.types.InputPeerUser(
                    user_id=file_id.chat_id, access_hash=file_id.chat_access_hash
                )
            else:
                if file_id.chat_access_hash == 0:
                    peer = raw.types.InputPeerChat(chat_id=-file_id.chat_id)
                else:
                    peer = raw.types.InputPeerChannel(
                        channel_id=utils.get_channel_id(file_id.chat_id),
                        access_hash=file_id.chat_access_hash,
                    )

            location = raw.types.InputPeerPhotoFileLocation(
                peer=peer,
                volume_id=file_id.volume_id,
                local_id=file_id.local_id,
                big=file_id.thumbnail_source == ThumbnailSource.CHAT_PHOTO_BIG,
            )
        elif file_type == FileType.PHOTO:
            location = raw.types.InputPhotoFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )
        else:
            location = raw.types.InputDocumentFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )
        return location

    async def yield_file(
        self,
        file_id: FileId,
        index: int,
        offset: int,
        first_part_cut: int,
        last_part_cut: int,
        part_count: int,
        chunk_size: int,
    ) -> Union[str, None]:
        """
        Generator that yields file chunks with proper error handling.
        Supports multiple concurrent users.
        """
        client = self.client
        work_loads[index] = work_loads.get(index, 0) + 1
        
        media_session = None
        current_part = 1
        
        try:
            media_session = await self.generate_media_session(client, file_id)
            location = await self.get_location(file_id)
            
            while current_part <= part_count:
                chunk = await self._fetch_chunk_with_retry(
                    media_session, location, offset, chunk_size
                )
                
                if chunk is None:
                    break
                
                # Process chunk based on position
                if part_count == 1:
                    yield chunk[first_part_cut:last_part_cut]
                elif current_part == 1:
                    yield chunk[first_part_cut:]
                elif current_part == part_count:
                    yield chunk[:last_part_cut]
                else:
                    yield chunk

                current_part += 1
                offset += chunk_size
                
        except asyncio.CancelledError:
            # Client cancelled the request (closed browser)
            logger.debug(f"Stream cancelled by client for index {index}")
        except (BrokenPipeError, ConnectionResetError, ConnectionError, OSError) as e:
            # Client disconnected - this is normal
            logger.debug(f"Client disconnected: {type(e).__name__}")
        except Exception as e:
            logger.warning(f"Stream error: {e}")
        finally:
            work_loads[index] = max(0, work_loads.get(index, 1) - 1)
            logger.debug(f"Stream completed: {current_part - 1} parts sent")

    async def _fetch_chunk_with_retry(
        self, 
        media_session: Session, 
        location, 
        offset: int, 
        chunk_size: int,
        max_retries: int = 3
    ) -> Optional[bytes]:
        """Fetch a single chunk with retry logic"""
        
        for attempt in range(max_retries):
            try:
                r = await asyncio.wait_for(
                    media_session.send(
                        raw.functions.upload.GetFile(
                            location=location, 
                            offset=offset, 
                            limit=chunk_size
                        )
                    ),
                    timeout=30  # 30 second timeout per chunk
                )
                
                if isinstance(r, raw.types.upload.File):
                    return r.bytes if r.bytes else None
                return None
                
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    logger.debug(f"Chunk timeout, retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(1)
                else:
                    logger.debug("Chunk timeout after all retries")
                    return None
                    
            except FloodWait as e:
                logger.warning(f"FloodWait in chunk fetch: {e.value}s")
                await asyncio.sleep(e.value)
                
            except (OSError, BrokenPipeError, ConnectionResetError) as e:
                # Connection error - client likely disconnected
                logger.debug(f"Connection error: {e}")
                return None
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.debug(f"Chunk error, retry {attempt + 1}: {e}")
                    await asyncio.sleep(1)
                else:
                    logger.warning(f"Chunk fetch failed: {e}")
                    return None
        
        return None


async def cleanup_sessions():
    """Cleanup function to be called on shutdown"""
    await _session_pool.close_all()
    await _file_cache.clear()
