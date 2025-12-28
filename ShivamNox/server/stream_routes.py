# Fixed for high traffic - Multiple concurrent users support
# Based on megadlbot_oss

import re
import time
import math
import logging
import secrets
import mimetypes
import asyncio
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
from ShivamNox.bot import multi_clients, work_loads, StreamBot
from ShivamNox.server.exceptions import FIleNotFound, InvalidHash
from ShivamNox import StartTime, __version__
from ..utils.time_format import get_readable_time
from ..utils.custom_dl import ByteStreamer
from ShivamNox.utils.render_template import render_page
from ShivamNox.vars import Var

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()

# Connection tracking
active_connections = 0
MAX_CONNECTIONS = 100  # Adjust based on your server capacity


@routes.get("/", allow_head=True)
async def root_route_handler(_):
    return web.json_response(
        {
            "server_status": "running",
            "uptime": get_readable_time(time.time() - StartTime),
            "telegram_bot": "@" + StreamBot.username,
            "connected_bots": len(multi_clients),
            "active_streams": active_connections,
            "loads": dict(
                ("bot" + str(c + 1), l)
                for c, (_, l) in enumerate(
                    sorted(work_loads.items(), key=lambda x: x[1], reverse=True)
                )
            ),
            "version": __version__,
        }
    )


@routes.get("/health", allow_head=True)
async def health_check(_):
    """Health check endpoint"""
    return web.json_response({"status": "healthy", "connections": active_connections})


@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def watch_handler(request: web.Request):
    try:
        path = request.match_info["path"]

        if path.lower() == "favicon.ico":
            return web.Response(status=204)

        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            match = re.search(r"(\d+)(?:\/\S+)?", path)
            if not match:
                raise web.HTTPBadRequest(text="Invalid URL format")
            id = int(match.group(1))
            secure_hash = request.rel_url.query.get("hash")
        
        html = await render_page(id, secure_hash)
        return web.Response(text=html, content_type='text/html')
    
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError, 
            BrokenPipeError, ConnectionError):
        return web.Response(status=499)
    except Exception as e:
        logger.error(f"Watch error: {e}")
        raise web.HTTPInternalServerError(text="Server error")


@routes.get(r"/{path:\S+}", allow_head=True)
async def generic_stream_handler(request: web.Request):
    global active_connections
    
    # Check connection limit
    if active_connections >= MAX_CONNECTIONS:
        return web.Response(
            status=503,
            text="Server busy, please try again later",
            headers={"Retry-After": "30"}
        )
    
    try:
        path = request.match_info["path"]

        if path.lower() == "favicon.ico":
            return web.Response(status=204)

        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            match = re.search(r"(\d+)(?:\/\S+)?", path)
            if not match:
                raise web.HTTPBadRequest(text="Invalid URL format")
            id = int(match.group(1))
            secure_hash = request.rel_url.query.get("hash")

        return await media_streamer(request, id, secure_hash)

    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError,
            BrokenPipeError, ConnectionError, OSError):
        return web.Response(status=499)
    except Exception as e:
        logger.error(f"Stream error: {e}")
        raise web.HTTPInternalServerError(text="Server error")


# Cache for ByteStreamer instances per client
class_cache = {}
_cache_lock = asyncio.Lock()


async def get_streamer(client) -> ByteStreamer:
    """Get or create ByteStreamer for a client (thread-safe)"""
    async with _cache_lock:
        if client not in class_cache:
            class_cache[client] = ByteStreamer(client)
        return class_cache[client]


async def media_streamer(request: web.Request, id: int, secure_hash: str):
    global active_connections
    
    active_connections += 1
    
    try:
        range_header = request.headers.get("Range", 0)
        
        # Select least loaded client
        if not work_loads:
            work_loads[0] = 0
        
        index = min(work_loads, key=work_loads.get)
        faster_client = multi_clients.get(index)
        
        if not faster_client:
            faster_client = multi_clients.get(0)
            index = 0
        
        if Var.MULTI_CLIENT:
            logger.debug(f"Client {index} serving {request.remote}")

        # Get ByteStreamer instance
        tg_connect = await get_streamer(faster_client)
        
        # Get file properties with timeout
        try:
            file_id = await asyncio.wait_for(
                tg_connect.get_file_properties(id),
                timeout=30
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout getting file properties for {id}")
            raise FIleNotFound
        
        # Verify hash
        if file_id.unique_id[:6] != secure_hash:
            raise InvalidHash
        
        file_size = file_id.file_size

        # Parse range header
        if range_header:
            from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
            from_bytes = int(from_bytes)
            until_bytes = int(until_bytes) if until_bytes else file_size - 1
        else:
            from_bytes = request.http_range.start or 0
            until_bytes = (request.http_range.stop or file_size) - 1

        # Validate range
        if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
            return web.Response(
                status=416,
                body="416: Range not satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"},
            )

        chunk_size = 1024 * 1024  # 1MB chunks
        until_bytes = min(until_bytes, file_size - 1)

        offset = from_bytes - (from_bytes % chunk_size)
        first_part_cut = from_bytes - offset
        last_part_cut = until_bytes % chunk_size + 1

        req_length = until_bytes - from_bytes + 1
        part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
        
        # Create safe body generator
        async def safe_body():
            try:
                async for chunk in tg_connect.yield_file(
                    file_id, index, offset, first_part_cut, 
                    last_part_cut, part_count, chunk_size
                ):
                    if chunk:
                        yield chunk
            except (ConnectionError, BrokenPipeError, ConnectionResetError, OSError):
                # Client disconnected
                pass
            except asyncio.CancelledError:
                # Request cancelled
                pass
            except Exception as e:
                logger.debug(f"Stream body error: {e}")

        # Determine mime type and filename
        mime_type = file_id.mime_type
        file_name = file_id.file_name
        disposition = "attachment"

        if mime_type:
            if not file_name:
                try:
                    file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
                except (IndexError, AttributeError):
                    file_name = f"{secrets.token_hex(2)}.unknown"
        else:
            if file_name:
                mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
            else:
                mime_type = "application/octet-stream"
                file_name = f"{secrets.token_hex(2)}.unknown"

        return web.Response(
            status=206 if range_header else 200,
            body=safe_body(),
            headers={
                "Content-Type": f"{mime_type}",
                "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
                "Content-Length": str(req_length),
                "Content-Disposition": f'{disposition}; filename="{file_name}"',
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600",
            },
        )
        
    finally:
        active_connections -= 1
