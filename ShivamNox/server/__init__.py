# © agrprojects - Updated for high traffic

import logging
from aiohttp import web
from .stream_routes import routes

logger = logging.getLogger(__name__)


async def web_server():
    async def error_middleware(app, handler):
        async def middleware_handler(request):
            try:
                return await handler(request)
            except web.HTTPException:
                raise
            except (ConnectionResetError, BrokenPipeError, ConnectionError, OSError):
                return web.Response(status=499)
            except Exception as e:
                logger.error(f"Unhandled error: {e}")
                return web.Response(status=500, text="Internal Server Error")
        return middleware_handler
    
    web_app = web.Application(
        client_max_size=30000000,
        middlewares=[error_middleware]
    )
    web_app.add_routes(routes)
    
    return web_app
