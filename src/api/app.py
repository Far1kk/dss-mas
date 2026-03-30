from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from src.api.routes import routes
from src.db.engine import init_db
from src.logger import log


@asynccontextmanager
async def lifespan(app):
    log.info("Запуск DSS-MAS...")
    await init_db()
    log.info("DSS-MAS готов к работе")
    yield
    log.info("Завершение работы DSS-MAS")


def create_app() -> Starlette:
    middleware = [
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
        Middleware(GZipMiddleware, minimum_size=1000),
    ]

    app = Starlette(
        debug=False,
        routes=routes,
        middleware=middleware,
        lifespan=lifespan,
    )
    return app
