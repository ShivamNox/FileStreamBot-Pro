# © agrprojects - Updated for high traffic

from aiohttp import web
from .stream_routes import routes


async def web_server():
    web_app = web.Application(
        client_max_size=30000000,  # 30MB max upload
        # Connection handling for high traffic
    )
    web_app.add_routes(routes)
    
    # Add middleware for connection tracking
    @web.middleware
    async def error_middleware(request, handler):
        try:
            return await handler(request)
        except web.HTTPException:
            raise
        except (ConnectionResetError, BrokenPipeError, ConnectionError):
            # Client disconnected - return empty response
            return web.Response(status=499)
        except Exception as e:
            logging.error(f"Unhandled error: {e}")
            return web.Response(status=500, text="Internal Server Error")
    
    return web_app
